"""
All external data fetching for The River Report.

Design rule: nothing in here is allowed to crash the run. Every fetch is wrapped
so that a failure returns an empty/placeholder result and the paper still ships.
Sources used:
  - yfinance  (no key)     : data strip, overseas closes, sector ETF moves
  - Polygon   (your key)   : index movers, market news
  - Guardian  (free key)   : world / political desks   [activates when key added]
  - FRED      (free key)   : treasury yields            [optional; yfinance covers it]
"""

import os
import re
import time
import datetime as dt
from zoneinfo import ZoneInfo

import requests

from . import config

POLYGON_KEY = os.environ.get("POLYGON_API_KEY", "").strip()
GUARDIAN_KEY = os.environ.get("GUARDIAN_API_KEY", "").strip()
NYT_KEY = os.environ.get("NYT_API_KEY", "").strip()
FRED_KEY = os.environ.get("FRED_API_KEY", "").strip()

POLYGON = "https://api.polygon.io"
GUARDIAN = "https://content.guardianapis.com/search"
NYT = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
HTTP_TIMEOUT = 25
# Symbols quoted as yields (shown as a % and changed in basis points). "2YY=F"
# is the CBOT 2-Year micro-yield future used for the strip's 2-Year cell.
YIELD_SYMBOLS = {"^TNX", "^FVX", "^TYX", "^IRX", "2YY=F"}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _fmt_value(symbol, v):
    """Format a raw number for display based on what kind of instrument it is."""
    if symbol in YIELD_SYMBOLS:
        return f"{v:,.2f}%"
    if symbol == "BTC-USD":
        return f"${v:,.0f}"
    if symbol in ("CL=F", "GC=F", "SI=F"):
        return f"${v:,.2f}"
    if abs(v) >= 1000:
        return f"{v:,.0f}" if v == int(v) or abs(v) >= 10000 else f"{v:,.2f}"
    return f"{v:,.2f}"


def _fmt_change(symbol, last, prior):
    """Return (change_string, direction) where direction is 'up' or 'down'."""
    if prior in (None, 0):
        return ("n/a", "flat")
    up = last >= prior
    arrow_dir = "up" if up else "down"
    if symbol in YIELD_SYMBOLS:
        bps = (last - prior) * 100.0
        return (f"{bps:+.0f} bps", arrow_dir)
    pct = (last - prior) / abs(prior) * 100.0
    return (f"{pct:+.2f}%", arrow_dir)


def _yahoo_batch(symbols):
    """
    Return {symbol: (last_close, prior_close)} for the given symbols.
    Missing or failed symbols are simply absent from the dict.
    """
    out = {}
    try:
        import yfinance as yf
        data = yf.download(
            tickers=" ".join(symbols),
            period="7d",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        return out

    for sym in symbols:
        try:
            if len(symbols) == 1:
                closes = data["Close"].dropna()
            else:
                closes = data[sym]["Close"].dropna()
            if len(closes) >= 2:
                out[sym] = (float(closes.iloc[-1]), float(closes.iloc[-2]))
            elif len(closes) == 1:
                out[sym] = (float(closes.iloc[-1]), None)
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# Data strip and overseas closes (yfinance, no key)
# ---------------------------------------------------------------------------
def get_strip(strip_config):
    symbols = [s for _, s in strip_config]
    quotes = _yahoo_batch(symbols)
    rows = []
    for label, sym in strip_config:
        if sym in quotes:
            last, prior = quotes[sym]
            change, direction = _fmt_change(sym, last, prior)
            rows.append({
                "label": label,
                "value": _fmt_value(sym, last),
                "change": change,
                "direction": direction,
            })
        else:
            rows.append({"label": label, "value": "n/a", "change": "", "direction": "flat"})
    return rows


def get_overseas():
    symbols = [s for _, _, s in config.OVERSEAS]
    quotes = _yahoo_batch(symbols)
    rows = []
    for name, region, sym in config.OVERSEAS:
        if sym in quotes:
            last, prior = quotes[sym]
            change, direction = _fmt_change(sym, last, prior)
            rows.append({"name": name, "region": region,
                         "value": _fmt_value(sym, last),
                         "change": change, "direction": direction})
        else:
            rows.append({"name": name, "region": region,
                         "value": "n/a", "change": "", "direction": "flat"})
    return rows


def get_sector_moves():
    """{sector_name: {'change': '+1.1%', 'direction': 'up'}} from sector SPDR ETFs.
    A sector whose ETF field is a tuple (e.g. Consumer -> XLY+XLP) shows the
    average of its constituent ETFs' percent moves."""
    etf_lists = {name: (list(etf) if isinstance(etf, (list, tuple)) else [etf])
                 for name, etf, _ in config.SECTORS}
    symbols = sorted({s for lst in etf_lists.values() for s in lst})
    quotes = _yahoo_batch(symbols)
    out = {}
    for name, etfs in etf_lists.items():
        pcts = [(last - prior) / abs(prior) * 100.0
                for etf in etfs if etf in quotes
                for last, prior in [quotes[etf]] if prior]
        if pcts:
            avg = sum(pcts) / len(pcts)
            out[name] = {"change": f"{avg:+.2f}%", "direction": "up" if avg >= 0 else "down"}
        else:
            out[name] = {"change": "", "direction": "flat"}
    return out


# ---------------------------------------------------------------------------
# Index membership (live fetch with fallbacks)
# ---------------------------------------------------------------------------
def _read_wikipedia_tables(url):
    import io
    import pandas as pd
    headers = {"User-Agent": "Mozilla/5.0 (AlphaArticle data fetch)"}
    html = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT).text
    # pandas 2.x no longer accepts a literal HTML string here -- it tries to read
    # it as a file path/URL and raises. Wrap it in StringIO. (This was the bug
    # that silently emptied every Wikipedia index's membership.)
    return pd.read_html(io.StringIO(html))


def _norm(t):
    """Canonical ticker form so Wikipedia / iShares symbols line up with
    Polygon's grouped-daily tickers. Polygon writes share classes with a dash
    (BRK-B); Wikipedia writes them with a dot (BRK.B). Fold both to the dash
    form, strip whitespace/quotes, and uppercase."""
    return (str(t).strip().strip('"').upper()
            .replace(" ", "").replace(".", "-"))


def get_constituents(index_name):
    """Return (set_of_tickers, {ticker: company_name})."""
    try:
        if index_name == "S&P 500":
            tables = _read_wikipedia_tables(
                "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
            df = tables[0]
            tickers, names = set(), {}
            for _, row in df.iterrows():
                t = _norm(row["Symbol"])
                tickers.add(t)
                names[t] = str(row.get("Security", "")).strip()
            if tickers:
                return tickers, names

        elif index_name == "Nasdaq 100":
            tables = _read_wikipedia_tables("https://en.wikipedia.org/wiki/Nasdaq-100")
            for df in tables:
                cols = [str(c).lower() for c in df.columns]
                tcol = next((df.columns[i] for i, c in enumerate(cols)
                             if "ticker" in c or "symbol" in c), None)
                ncol = next((df.columns[i] for i, c in enumerate(cols)
                             if "company" in c or "security" in c), None)
                if tcol is not None and len(df) > 80:
                    tickers, names = set(), {}
                    for _, row in df.iterrows():
                        t = _norm(row[tcol])
                        tickers.add(t)
                        if ncol is not None:
                            names[t] = str(row[ncol]).strip()
                    return tickers, names

        elif index_name == "Dow 30":
            tables = _read_wikipedia_tables(
                "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average")
            for df in tables:
                cols = [str(c).lower() for c in df.columns]
                tcol = next((df.columns[i] for i, c in enumerate(cols)
                             if "symbol" in c or "ticker" in c), None)
                ncol = next((df.columns[i] for i, c in enumerate(cols)
                             if "company" in c), None)
                if tcol is not None and 25 <= len(df) <= 40:
                    tickers, names = set(), {}
                    for _, row in df.iterrows():
                        t = _norm(row[tcol])
                        tickers.add(t)
                        if ncol is not None:
                            names[t] = str(row[ncol]).strip()
                    return tickers, names

        elif index_name == "Russell 2000":
            return _get_iwm_holdings()
    except Exception:
        pass

    # Fallbacks
    if index_name == "Dow 30":
        return set(config.DOW30_FALLBACK), {}
    return set(), {}


def _get_iwm_holdings():
    """Russell 2000 membership via the public iShares IWM holdings CSV.

    The .ajax endpoint serves the real CSV to ordinary browsers but an Akamai
    bot-wall sometimes answers a data-center IP with the HTML product page
    instead. We send browser-like headers and, if the body comes back as HTML
    rather than CSV, return empty so the caller degrades to "data unavailable"
    (never garbage, never a whole-market fallback)."""
    import csv
    import io
    url = ("https://www.ishares.com/us/products/239710/"
           "ishares-russell-2000-etf/1467271812596.ajax"
           "?fileType=csv&fileName=IWM_holdings&dataType=fund")
    text = requests.get(url, headers=_BROWSER_UA, timeout=HTTP_TIMEOUT).text
    if "<html" in text[:2000].lower() or "Ticker" not in text:
        return set(), {}   # bot-wall HTML, not the holdings CSV
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.lower().startswith("ticker") or '"Ticker"' in line:
            start = i
            break
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    tickers, names = set(), {}
    for row in reader:
        tk = (row.get("Ticker") or "").strip()
        asset = (row.get("Asset Class") or "Equity").strip()
        if tk and tk not in ("-", "") and "Equity" in asset:
            t = _norm(tk)
            tickers.add(t)
            names[t] = (row.get("Name") or "").strip().title()
    return tickers, names


# ---------------------------------------------------------------------------
# Movers (Polygon grouped daily for the whole US market)
# ---------------------------------------------------------------------------
def _grouped_daily(date_str):
    """All US stocks for one date: {ticker: close_price}."""
    if not POLYGON_KEY:
        return {}
    url = f"{POLYGON}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    try:
        r = requests.get(url, params={"adjusted": "true", "apiKey": POLYGON_KEY},
                         timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return {}
        results = r.json().get("results", []) or []
        return {row["T"]: row.get("c") for row in results if row.get("c")}
    except Exception:
        return {}


def _two_recent_sessions():
    """Find the two most recent trading days that return grouped data."""
    today = dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()
    found = []
    probe = today
    for _ in range(8):
        ds = probe.isoformat()
        data = _grouped_daily(ds)
        if data:
            found.append((ds, data))
            if len(found) == 2:
                break
        probe = probe - dt.timedelta(days=1)
        time.sleep(0.2)
    return found


def get_all_movers():
    """
    Compute winners/losers for every index in one shot so the whole-market
    grouped data is only fetched once.
    Returns {index_name: {'winners': [...], 'losers': [...]}}.
    """
    sessions = _two_recent_sessions()
    if len(sessions) < 2:
        print("[movers] grouped-daily feed returned < 2 sessions; movers unavailable")
        return {idx: {"winners": [], "losers": [], "unavailable": True}
                for idx in config.MOVERS_INDICES}

    (_, latest), (_, prior) = sessions[0], sessions[1]

    # Universe of percentage moves across the whole market, keyed by the same
    # normalized ticker form the constituent lists use.
    universe = {}
    for tk, c_now in latest.items():
        c_prev = prior.get(tk)
        if c_prev and c_now and c_now >= config.MIN_PRICE and c_prev > 0:
            key = _norm(tk)
            universe[key] = {
                "ticker": tk,
                "last": c_now,
                "pct": (c_now - c_prev) / c_prev * 100.0,
            }

    out = {}
    for idx in config.MOVERS_INDICES:
        members, names = get_constituents(idx)
        matched = sum(1 for t in members if t in universe)
        print(f"[movers] {idx}: resolved {len(members)} members "
              f"({matched} matched to today's tape)")
        if not members:
            # CRITICAL: never fall back to the whole market. If we can't resolve
            # an index's membership, that index shows a "data unavailable" state
            # instead of leaking non-members (e.g. FCUV/WLDSW under the S&P 500).
            out[idx] = {"winners": [], "losers": [], "unavailable": True}
            continue
        pool = [dict(universe[t], name=names.get(t, "")) for t in members if t in universe]
        pool.sort(key=lambda x: x["pct"], reverse=True)
        winners = pool[: config.TOP_N]
        losers = sorted(pool, key=lambda x: x["pct"])[: config.TOP_N]
        out[idx] = {"winners": winners, "losers": losers, "unavailable": False}
        time.sleep(0.1)
    return out


# ---------------------------------------------------------------------------
# News (Polygon)
# ---------------------------------------------------------------------------
def _polygon_news(limit=1000):
    if not POLYGON_KEY:
        return []
    url = f"{POLYGON}/v2/reference/news"
    try:
        r = requests.get(url, params={"limit": min(limit, 1000),
                                      "order": "desc", "sort": "published_utc",
                                      "apiKey": POLYGON_KEY}, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return []
        return r.json().get("results", []) or []
    except Exception:
        return []


def _publisher_allowed(name):
    """True only for the high-quality publishers in the allowlist. 'ap' is
    matched as a standalone word so it can't swallow unrelated names."""
    n = (name or "").lower()
    for term in config.NEWS_PUBLISHER_ALLOWLIST:
        if term == "ap":
            if re.search(r"\bap\b", n):
                return True
        elif term in n:
            return True
    return False


def _title_blocked(title):
    """True if a headline carries class-action / 'investor alert' spam markers."""
    t = (title or "").lower()
    return any(b in t for b in config.NEWS_TITLE_BLOCKLIST)


def _news_ok(art):
    """Keep a Polygon news item only if its publisher is allowlisted AND its
    title is free of the law-firm/PR-spam patterns."""
    pub = (art.get("publisher") or {}).get("name", "")
    return _publisher_allowed(pub) and not _title_blocked(art.get("title") or "")


def get_sector_desk():
    """
    For each sector: its ETF move plus the latest headlines whose tickers match
    the sector's bellwethers. One news fetch, bucketed across all sectors.
    """
    moves = get_sector_moves()
    news = _polygon_news(limit=1000)

    sector_of = {}
    for name, _, tickers in config.SECTORS:
        for t in tickers:
            sector_of[_norm(t)] = name

    buckets = {name: [] for name, _, _ in config.SECTORS}
    seen = {name: set() for name, _, _ in config.SECTORS}
    for art in news:
        if not _news_ok(art):
            continue  # drop PR-wire spam and class-action filings
        arts_tickers = [_norm(t) for t in (art.get("tickers") or [])]
        for t in arts_tickers:
            sec = sector_of.get(t)
            if sec and len(buckets[sec]) < config.NEWS_PER_BLOCK:
                title = (art.get("title") or "").strip()
                if title and title not in seen[sec]:
                    seen[sec].add(title)
                    buckets[sec].append({
                        "ticker": t,
                        "title": title,
                        "url": art.get("article_url", ""),
                        "publisher": (art.get("publisher") or {}).get("name", ""),
                    })
                break

    desk = []
    for name, etf, _ in config.SECTORS:
        desk.append({
            "name": name,
            "move": moves.get(name, {}).get("change", ""),
            "direction": moves.get(name, {}).get("direction", "flat"),
            "items": buckets[name],
        })
    return desk


def get_market_headlines(n=16):
    """Latest market headlines for the lead and the overnight block. Real
    journalism from NYT Business and Guardian business is blended in front of
    the (allowlist-filtered) Polygon wire items, so the lead is a reported
    story rather than a ticker-tagged press release."""
    poly = []
    for art in _polygon_news(limit=200):
        if not _news_ok(art):
            continue  # drop PR-wire spam and class-action filings
        title = (art.get("title") or "").strip()
        if not title:
            continue
        poly.append({
            "title": title,
            "url": art.get("article_url", ""),
            "publisher": (art.get("publisher") or {}).get("name", ""),
            "tickers": art.get("tickers") or [],
        })

    nyt = _blank_tickers(get_nyt_business(n=8))
    guardian = _blank_tickers(get_guardian_business(n=8))

    # Round-robin the three sources so the lead favors reported journalism but
    # the list still carries fresh wire items underneath.
    out, seen = [], set()
    for art in _interleave(nyt, guardian, poly):
        title = (art.get("title") or "").strip()
        key = title.lower()
        if title and key not in seen:
            seen.add(key)
            out.append(art)
        if len(out) >= n:
            break
    return out


def _blank_tickers(stories):
    """NYT/Guardian items carry no tickers; normalize them to the headline shape
    get_market_headlines / the renderer expect."""
    return [{"title": s.get("title", ""), "url": s.get("url", ""),
             "publisher": s.get("publisher", ""), "tickers": []}
            for s in stories]


def _interleave(*lists):
    """Round-robin merge: first of each list, then second of each, etc."""
    out = []
    for i in range(max((len(x) for x in lists), default=0)):
        for lst in lists:
            if i < len(lst):
                out.append(lst[i])
    return out


def get_guardian_business(n=8):
    """Market-insight stories from the Guardian business section."""
    return _guardian_search(section="business", n=n)


def get_nyt_business(n=8):
    """Market-insight stories from the NYT Business desk."""
    return _nyt_section("Business", n=n)


# ---------------------------------------------------------------------------
# Regional desks (The Guardian + The New York Times)
#
# Six regional desks, each with a "Politics" and a "Macro & Markets"
# sub-section, populated from the Guardian and NYT search APIs. Keys come from
# GUARDIAN_API_KEY / NYT_API_KEY and may be empty -- every fetch is wrapped so a
# missing key or a failure simply yields [] and the desk shows a placeholder.
# Only the API-provided summary field (Guardian trailText / NYT abstract) is
# used; full article bodies are never reprinted.
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text):
    """Strip any HTML tags the summary fields carry and collapse whitespace."""
    return _TAG_RE.sub("", str(text or "")).strip()


def _guardian_search(section=None, q=None, n=None):
    n = n or config.NEWS_PER_BLOCK
    if not GUARDIAN_KEY:
        return []
    params = {"page-size": n, "order-by": "newest",
              "show-fields": "trailText", "api-key": GUARDIAN_KEY}
    if section:
        params["section"] = section
    if q:
        params["q"] = q
    try:
        r = requests.get(GUARDIAN, params=params, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return []
        results = r.json().get("response", {}).get("results", []) or []
        out = []
        for x in results:
            fields = x.get("fields") or {}
            out.append({"title": x.get("webTitle", ""),
                        "url": x.get("webUrl", ""),
                        "summary": _clean(fields.get("trailText", "")),
                        "section": (x.get("sectionId") or "").lower(),
                        "publisher": "The Guardian"})
        return out
    except Exception:
        return []


def _nyt_search(q=None, n=None):
    n = n or config.NEWS_PER_BLOCK
    if not NYT_KEY:
        return []
    params = {"sort": "newest", "api-key": NYT_KEY}
    if q:
        params["q"] = q
    return _nyt_request(params, n)


def _nyt_section(desk, n=None):
    """Newest NYT stories from a given news desk (e.g. 'Business', 'Foreign')."""
    n = n or config.NEWS_PER_BLOCK
    if not NYT_KEY:
        return []
    return _nyt_request({"sort": "newest", "fq": f'news_desk:("{desk}")',
                         "api-key": NYT_KEY}, n)


def _nyt_request(params, n):
    try:
        r = requests.get(NYT, params=params, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return []
        docs = r.json().get("response", {}).get("docs", []) or []
        out = []
        for d in docs[:n]:
            headline = (d.get("headline") or {}).get("main", "")
            out.append({"title": headline,
                        "url": d.get("web_url", ""),
                        "summary": _clean(d.get("abstract") or d.get("snippet")),
                        "section": (d.get("news_desk") or d.get("section_name")
                                    or "").lower(),
                        "publisher": "The New York Times"})
        return out
    except Exception:
        return []


def _regional_pool():
    """One bulk pull of world / business / political stories from the Guardian
    and the NYT. Each story is later assigned to exactly one desk."""
    pool = []
    for section in ("world", "us-news", "politics", "business"):
        pool += _guardian_search(section=section, n=12)
    pool += _nyt_section("Foreign", n=12)
    pool += _nyt_section("Business", n=12)
    pool += _nyt_section("Politics", n=8)
    return pool


def _normtext(s):
    """Lowercase, collapse every run of non-alphanumerics to a single space, and
    pad with spaces. Whole-word keyword tests become a simple ' kw ' substring
    check -- so 'us' matches the token US but never the 'us' inside 'business'."""
    return " " + re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip() + " "


def _kw_hit(kw, padded):
    """True if normalized keyword kw appears as a whole token-run in padded."""
    k = re.sub(r"[^a-z0-9]+", " ", kw.lower()).strip()
    return f" {k} " in padded


def _assign_region(title, summary):
    """Assign a story to exactly one region. Returns the region name. A specific
    country/capital (weight 2) beats a generic regional term (weight 1); ties go
    to the lower-priority number (foreign desks outrank Washington). Anything
    that matches nothing falls through to 'The Rest of the World'."""
    padded = _normtext(f"{title} {summary}")
    best_name, best_weight, best_priority = None, 0, 99
    for name in config.REGION_ORDER:
        spec = config.REGION_KEYWORDS[name]
        priority = spec["priority"]
        weight = 0
        if any(_kw_hit(k, padded) for k in spec["specific"]):
            weight = 2
        elif any(_kw_hit(k, padded) for k in spec["generic"]):
            weight = 1
        if weight == 0:
            continue
        if weight > best_weight or (weight == best_weight and priority < best_priority):
            best_name, best_weight, best_priority = name, weight, priority
    return best_name or "The Rest of the World"


def _classify(story):
    """Split a story into 'macro' or 'politics'. A business/economy/markets
    source section forces macro; otherwise the title+summary keyword balance
    decides, defaulting to politics."""
    section = story.get("section", "")
    if any(s in section for s in ("business", "money", "econom", "market")):
        return "macro"
    text = f"{story.get('title','')} {story.get('summary','')}".lower()
    macro = sum(1 for t in config.NEWS_MACRO_TERMS if t in text)
    politics = sum(1 for t in config.NEWS_POLITICS_TERMS if t in text)
    return "macro" if macro > politics else "politics"


def get_regional_desks():
    """Return the six regional desks, each {name, politics:[...], macro:[...]}.
    Every story is assigned to exactly ONE desk and ONE sub-section, and is
    deduped globally so it can never appear twice anywhere in the paper. Each
    story: {title, summary, url, publisher}. Never raises."""
    desks = {name: {"politics": [], "macro": []} for name in config.REGION_ORDER}
    try:
        pool = _regional_pool()
    except Exception:
        pool = []

    seen_urls, seen_titles = set(), set()
    for story in pool:
        title = (story.get("title") or "").strip()
        url = (story.get("url") or "").strip()
        tkey = title.lower()
        if not title or tkey in seen_titles or (url and url in seen_urls):
            continue  # global dedupe: one appearance per story, paper-wide
        seen_titles.add(tkey)
        if url:
            seen_urls.add(url)

        region = _assign_region(title, story.get("summary", ""))
        kind = _classify(story)
        bucket = desks[region][kind]
        if len(bucket) < config.NEWS_PER_BLOCK:
            bucket.append({"title": title, "url": url,
                           "summary": story.get("summary", ""),
                           "publisher": story.get("publisher", "")})

    return [{"name": name, "politics": desks[name]["politics"],
             "macro": desks[name]["macro"]} for name in config.REGION_ORDER]


# ---------------------------------------------------------------------------
# Forward calendar -- "The Day Ahead". Free, keyless sources, each wrapped so a
# failure (or a blocked request from CI) just yields [] and the section shows
# "None scheduled" rather than the old placeholder.
#   - Economic releases: Trading Economics guest calendar (United States)
#   - Earnings:          Nasdaq earnings calendar API
# ---------------------------------------------------------------------------
_BROWSER_UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _to_et_time(iso_utc):
    """'2026-06-24T12:30:00' (UTC) -> '7:30 AM' US Eastern. '' on any failure."""
    try:
        s = str(iso_utc).replace("Z", "").strip()
        d = dt.datetime.fromisoformat(s).replace(tzinfo=ZoneInfo("UTC"))
        et = d.astimezone(ZoneInfo("America/New_York"))
        return et.strftime("%-I:%M %p") if _has_dash() else et.strftime("%I:%M %p")
    except Exception:
        return ""


def _has_dash():
    try:
        dt.datetime.now().strftime("%-I")
        return True
    except Exception:
        return False


def _economic_calendar():
    """US economic releases for today + tomorrow via Trading Economics' free
    guest endpoint. Returns [{time, event, consensus, prior}]."""
    today = dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()
    d1 = today.isoformat()
    d2 = (today + dt.timedelta(days=1)).isoformat()
    url = f"https://api.tradingeconomics.com/calendar/country/united%20states/{d1}/{d2}"
    try:
        r = requests.get(url, params={"c": "guest:guest", "f": "json"},
                         headers=_BROWSER_UA, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return []
        rows = r.json() or []
    except Exception:
        return []
    out = []
    for row in rows:
        event = (row.get("Event") or "").strip()
        if not event:
            continue
        out.append({
            "time": _to_et_time(row.get("Date")),
            "event": event,
            "consensus": str(row.get("Forecast") or "").strip() or "-",
            "prior": str(row.get("Previous") or "").strip() or "-",
        })
        if len(out) >= config.CAL_ECON_N:
            break
    return out


def _nasdaq_earnings_day(date_str):
    url = "https://api.nasdaq.com/api/calendar/earnings"
    try:
        r = requests.get(url, params={"date": date_str}, headers=_BROWSER_UA,
                         timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            return []
        return (r.json().get("data") or {}).get("rows") or []
    except Exception:
        return []


def _mktcap(row):
    try:
        return float(re.sub(r"[^0-9.]", "", row.get("marketCap") or "") or 0)
    except Exception:
        return 0.0


_EARNINGS_TIME = {"time-pre-market": "Before open", "time-after-hours": "After close"}


def _earnings_calendar():
    """Notable companies reporting today + tomorrow via the Nasdaq earnings
    calendar, largest by market cap first. Returns [{ticker, name, time, eps}]."""
    today = dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()
    rows = []
    for offset in (0, 1):
        rows += _nasdaq_earnings_day((today + dt.timedelta(days=offset)).isoformat())
    by_symbol = {}
    for row in rows:
        sym = (row.get("symbol") or "").strip().upper()
        if sym and sym not in by_symbol:
            by_symbol[sym] = row
    ranked = sorted(by_symbol.values(), key=_mktcap, reverse=True)
    out = []
    for row in ranked[: config.CAL_EARNINGS_N]:
        out.append({
            "ticker": (row.get("symbol") or "").strip().upper(),
            "name": (row.get("name") or "").strip(),
            "time": _EARNINGS_TIME.get(row.get("time") or "", ""),
            "eps": str(row.get("epsForecast") or "").strip() or "-",
        })
    return out


def get_calendar():
    """Real forward calendar: US economic releases and notable earnings for
    today + tomorrow. Either source may come back empty (the renderer then shows
    'None scheduled'); connected is True now that real sources are wired in."""
    try:
        economic = _economic_calendar()
    except Exception:
        economic = []
    try:
        earnings = _earnings_calendar()
    except Exception:
        earnings = []
    return {"economic": economic, "earnings": earnings, "connected": True}
