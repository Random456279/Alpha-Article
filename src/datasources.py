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
    import pandas as pd
    headers = {"User-Agent": "Mozilla/5.0 (AlphaArticle data fetch)"}
    html = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT).text
    return pd.read_html(html)


def _norm(t):
    return str(t).strip().upper().replace(" ", "")


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
    """Russell 2000 membership via the public iShares IWM holdings CSV."""
    import csv
    import io
    url = ("https://www.ishares.com/us/products/239710/"
           "ishares-russell-2000-etf/1467271812596.ajax"
           "?fileType=csv&fileName=IWM_holdings&dataType=fund")
    headers = {"User-Agent": "Mozilla/5.0 (AlphaArticle data fetch)"}
    text = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT).text
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
        return {idx: {"winners": [], "losers": []} for idx in config.MOVERS_INDICES}

    (_, latest), (_, prior) = sessions[0], sessions[1]

    # Universe of percentage moves across the whole market.
    universe = {}
    for tk, c_now in latest.items():
        c_prev = prior.get(tk)
        if c_prev and c_now and c_now >= config.MIN_PRICE and c_prev > 0:
            universe[tk] = {
                "ticker": tk,
                "last": c_now,
                "pct": (c_now - c_prev) / c_prev * 100.0,
            }

    out = {}
    for idx in config.MOVERS_INDICES:
        members, names = get_constituents(idx)
        if members:
            pool = [dict(universe[t], name=names.get(t, "")) for t in members if t in universe]
        else:
            # No membership available: fall back to the whole market so the
            # section still shows something (mainly a safety net for R2000).
            pool = list(universe.values())
        pool.sort(key=lambda x: x["pct"], reverse=True)
        winners = pool[: config.TOP_N]
        losers = sorted(pool, key=lambda x: x["pct"])[: config.TOP_N]
        out[idx] = {"winners": winners, "losers": losers}
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
    """Latest market headlines, used for the lead and the overnight block."""
    news = _polygon_news(limit=50)
    out = []
    seen = set()
    for art in news:
        title = (art.get("title") or "").strip()
        if title and title not in seen:
            seen.add(title)
            out.append({
                "title": title,
                "url": art.get("article_url", ""),
                "publisher": (art.get("publisher") or {}).get("name", ""),
                "tickers": art.get("tickers") or [],
            })
        if len(out) >= n:
            break
    return out


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
                        "publisher": "The New York Times"})
        return out
    except Exception:
        return []


def _region_stories(region, kind):
    """Stories for one desk's sub-section. kind is 'politics' or 'macro'."""
    g = region.get("guardian", {})
    q = region.get("query")
    if kind == "politics":
        guardian = _guardian_search(section=g.get("politics"), q=q)
        nyt = _nyt_search(q=(f"{q} politics" if q else "politics"))
    else:
        macro_q = f"{q} economy markets" if q else "economy markets"
        guardian = _guardian_search(section=g.get("macro"), q=q)
        nyt = _nyt_search(q=macro_q)

    seen, out = set(), []
    for story in (guardian + nyt):
        title = (story.get("title") or "").strip()
        if title and title not in seen:
            seen.add(title)
            out.append(story)
        if len(out) >= config.NEWS_PER_BLOCK:
            break
    return out


def get_regional_desks():
    """Return the six regional desks, each {name, politics:[...], macro:[...]}.
    Each story: {title, summary, url, publisher}. Never raises."""
    desks = []
    for region in config.REGIONAL_DESKS:
        try:
            politics = _region_stories(region, "politics")
        except Exception:
            politics = []
        try:
            macro = _region_stories(region, "macro")
        except Exception:
            macro = []
        desks.append({"name": region["name"], "politics": politics, "macro": macro})
    return desks


# ---------------------------------------------------------------------------
# Forward calendar -- placeholder until a free source is wired in next session
# ---------------------------------------------------------------------------
def get_calendar():
    return {"economic": [], "earnings": [], "connected": False}
