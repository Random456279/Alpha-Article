"""
Renders The River Report. render() builds the complete GitHub Pages web edition;
render_email() builds the compact, Gmail-safe email twin. Black-and-white
WSJ-style broadsheet, serif type, hairline rules, tabular figures.
"""

import datetime as dt
import html
from zoneinfo import ZoneInfo

from . import config


def _issue_parts(issue):
    """(volume, number) from the issue dict build.py computes; defaults to 1/1
    so direct/preview calls without a persisted counter still render sensibly."""
    issue = issue or {}
    return issue.get("volume", 1), issue.get("number", 1)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=PT+Serif:ital,wght@0,400;0,700;1,400&display=swap');
body{margin:0;background:#e9e9e6;padding:18px}
.paper{max-width:760px;margin:0 auto;box-sizing:border-box;background:#FBFBF9;color:#141414;padding:30px 34px 24px;font-family:'PT Serif',Georgia,serif;line-height:1.45;border:1px solid #DcDcD8;font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}
.paper *{box-sizing:border-box}
.browserbar{max-width:760px;margin:0 auto 10px;text-align:center;font-family:'PT Serif',Georgia,serif;font-size:12px;letter-spacing:.5px}
.browserbar a{color:#333;text-decoration:underline}
.toprule{border-top:3px solid #141414;margin-bottom:12px}
.flag{font-family:'Playfair Display',Georgia,serif;font-weight:900;font-size:46px;letter-spacing:1px;text-transform:uppercase;text-align:center;line-height:1.02}
.meta{display:flex;justify-content:space-between;font-size:11px;text-transform:uppercase;letter-spacing:1px;padding:6px 2px;border-top:2px solid #141414;border-bottom:1px solid #141414;margin-top:12px}
.strip{display:flex;flex-wrap:wrap;border-bottom:2px solid #141414;border-left:1px solid #C7C7C7;margin:14px 0 16px}
.q{flex:0 0 25%;width:25%;padding:6px 9px;border-right:1px solid #C7C7C7;border-top:1px solid #C7C7C7}
.q .n{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#3a3a3a}
.q .v{font-size:15px;font-weight:700;line-height:1.25}
.q .c{font-size:11px}
.kick{font-size:11px;text-transform:uppercase;letter-spacing:2px;font-weight:700;border-bottom:1px solid #141414;display:inline-block;padding-bottom:2px;margin-bottom:7px}
.hl{font-family:'Playfair Display',Georgia,serif;font-weight:900;font-size:28px;line-height:1.08;margin:1px 0 6px}
.hl a{color:#141414;text-decoration:none}
.dateline{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#3a3a3a;margin-bottom:8px}
.lead-body{font-size:13px;line-height:1.5;text-align:justify;hyphens:auto}
.lead-body::first-letter{font-family:'Playfair Display',serif;font-weight:900;font-size:50px;line-height:.78;float:left;padding:5px 8px 0 0}
.sec{font-family:'Playfair Display',Georgia,serif;font-weight:900;font-size:13px;text-transform:uppercase;letter-spacing:3px;text-align:center;border-top:3px solid #141414;border-bottom:1px solid #141414;padding:6px 0;margin:22px 0 13px}
.idx{margin-bottom:16px}
.idxh{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1.5px solid #141414;padding-bottom:3px;margin-bottom:7px}
.idxh .nm{font-family:'Playfair Display',serif;font-weight:700;font-size:15px}
.idxh .px{font-size:12.5px}
.mv{display:flex;flex-wrap:wrap;gap:0 24px}
.mvcol{flex:1 1 270px}
.cap{display:flex;justify-content:space-between;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;font-weight:700;border-bottom:1px solid #141414;padding-bottom:2px;margin-bottom:3px}
table.t{width:100%;border-collapse:collapse;font-size:12px}
table.t td{padding:2.5px 0;border-bottom:1px solid #E4E4E2;vertical-align:baseline}
table.t .tk{font-weight:700}
table.t .co{font-size:11px;color:#5a5a5a}
table.t .num{text-align:right;white-space:nowrap}
.sectwrap{column-count:2;column-gap:26px;column-rule:1px solid #C7C7C7}
.sect{break-inside:avoid;margin-bottom:13px}
.secth{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1.5px solid #141414;padding-bottom:2px;margin-bottom:5px}
.snm{font-family:'Playfair Display',serif;font-weight:700;font-size:15px}
.spx{font-size:12px}
.sitem{font-size:12.5px;line-height:1.4;margin:0 0 5px}
.sitem a{color:#141414;text-decoration:none}
.tkr{font-weight:700}
.src{font-size:10.5px;color:#6a6a6a}
.muted{font-size:12px;font-style:italic;color:#6a6a6a}
.news{column-count:2;column-gap:26px;column-rule:1px solid #C7C7C7}
.art{break-inside:avoid;margin-bottom:11px}
.art .k{font-size:11px;text-transform:uppercase;letter-spacing:1.2px;font-weight:700;color:#3a3a3a}
.art h3{font-family:'Playfair Display',serif;font-weight:700;font-size:15px;line-height:1.12;margin:1px 0 3px}
.art h3 a{color:#141414;text-decoration:none}
.cal{display:flex;flex-wrap:wrap;gap:0 24px}
.calcol{flex:1 1 260px}
.ct{font-size:11px;text-transform:uppercase;letter-spacing:1.2px;font-weight:700;border-bottom:1.5px solid #141414;padding-bottom:2px;margin-bottom:4px}
table.c{width:100%;border-collapse:collapse;font-size:11.5px}
table.c td{padding:2.5px 0;border-bottom:1px solid #E4E4E2}
table.c .r{text-align:right;white-space:nowrap}
.ov{display:flex;flex-wrap:wrap;gap:0 24px}
.ovcol{flex:1 1 260px}
.ovrow{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #E4E4E2;padding:3px 0;gap:10px}
.foot{border-top:2px solid #141414;margin-top:20px;padding-top:8px;font-size:11px;color:#3a3a3a;text-align:center;line-height:1.45}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
.region{margin-bottom:18px;break-inside:avoid}
.rname{font-family:'Playfair Display',serif;font-weight:900;font-size:18px;border-bottom:2px solid #141414;padding-bottom:3px;margin-bottom:8px}
.rcols{display:flex;flex-wrap:wrap;gap:0 26px;column-rule:1px solid #C7C7C7}
.rsub{flex:1 1 300px}
.rsublabel{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;color:#3a3a3a;border-bottom:1px solid #C7C7C7;padding-bottom:2px;margin-bottom:6px}
.rstory{margin-bottom:10px}
.rh{font-family:'Playfair Display',serif;font-weight:700;font-size:14px;line-height:1.16;margin:0 0 2px}
.rh a{color:#141414;text-decoration:none}
.rsum{font-size:12px;line-height:1.42;margin:0 0 2px;color:#222}
"""


def _e(s):
    return html.escape(str(s), quote=True)


def _arrow(direction):
    return "\u25B2" if direction == "up" else ("\u25BC" if direction == "down" else "")


def _strip_html(rows):
    cells = []
    for r in rows:
        arrow = _arrow(r["direction"])
        chg = f"{arrow} {_e(r['change'])}" if r["change"] else ""
        cells.append(
            f'<div class="q"><div class="n">{_e(r["label"])}</div>'
            f'<div class="v">{_e(r["value"])}</div>'
            f'<div class="c">{chg}</div></div>')
    return '<div class="strip">' + "".join(cells) + "</div>"


def _lead_html(headlines):
    if headlines:
        top = headlines[0]
        title = _e(top["title"])
        link = top["url"]
        head = f'<a href="{_e(link)}">{title}</a>' if link else title
        pub = _e(top["publisher"]) if top["publisher"] else "Wire"
        framing = ("The session's most prominent market story leads the page; "
                   "the desks below carry movers, sectors, and the day's schedule.")
        return (
            f'<div class="kick">Markets</div>'
            f'<div class="hl">{head}</div>'
            f'<div class="dateline">{pub}</div>'
            f'<div class="lead-body">{framing}</div>')
    return (
        '<div class="kick">Markets</div>'
        '<div class="hl">Markets in Brief</div>'
        f'<div class="dateline">{_e(config.PAPER_NAME)}</div>'
        '<div class="lead-body">Headlines connect once the market news feed '
        'returns for this cycle. Movers, sectors, and the day ahead follow.</div>')


def _movers_table(rows):
    if not rows:
        return '<table class="t"><tr><td class="muted">No qualifying names.</td></tr></table>'
    body = []
    for r in rows:
        name = _e(r.get("name", "")) or ""
        co = f' <span class="co">{name}</span>' if name else ""
        body.append(
            f'<tr><td><span class="tk">{_e(r["ticker"])}</span>{co}</td>'
            f'<td class="num">{r["last"]:,.2f}</td>'
            f'<td class="num">{r["pct"]:+.1f}%</td></tr>')
    return '<table class="t">' + "".join(body) + "</table>"


def _movers_section(all_movers, index_levels):
    blocks = []
    any_data = False
    for idx in config.MOVERS_INDICES:
        data = all_movers.get(idx, {"winners": [], "losers": []})
        if data["winners"] or data["losers"]:
            any_data = True
        lvl = index_levels.get(idx, {})
        px = ""
        if lvl:
            arrow = _arrow(lvl.get("direction", "flat"))
            px = f'{_e(lvl.get("value",""))} &middot; {arrow} {_e(lvl.get("change",""))}'
        blocks.append(
            f'<div class="idx"><div class="idxh"><span class="nm">{_e(idx)}</span>'
            f'<span class="px">{px}</span></div>'
            f'<div class="mv"><div class="mvcol">'
            f'<div class="cap"><span>Winners</span><span>\u25B2</span></div>'
            f'{_movers_table(data["winners"])}</div>'
            f'<div class="mvcol">'
            f'<div class="cap"><span>Losers</span><span>\u25BC</span></div>'
            f'{_movers_table(data["losers"])}</div></div></div>')
    note = ""
    if not any_data:
        note = ('<div class="muted">Movers populate once the market-data feed '
                'returns two settled sessions for this run.</div>')
    return '<div class="sec">The Close &middot; Biggest Movers</div>' + note + "".join(blocks)


def _sector_section(desk):
    blocks = []
    for s in desk:
        arrow = _arrow(s["direction"])
        move = f'{arrow} {_e(s["move"])}' if s["move"] else ""
        if s["items"]:
            items = "".join(
                f'<p class="sitem"><span class="tkr">{_e(it["ticker"])}:</span> '
                f'<a href="{_e(it["url"])}">{_e(it["title"])}</a> '
                f'<span class="src">{_e(it["publisher"])}</span></p>'
                for it in s["items"])
        else:
            items = '<p class="muted">No flagged single-stock headlines this cycle.</p>'
        blocks.append(
            f'<div class="sect"><div class="secth"><span class="snm">{_e(s["name"])}</span>'
            f'<span class="spx">{move}</span></div>{items}</div>')
    return ('<div class="sec">The Sector Desk</div>'
            '<div class="sectwrap">' + "".join(blocks) + "</div>")


def _region_story_full(s):
    """One regional story: headline + the API summary + the linked source."""
    title = _e(s.get("title", ""))
    url = s.get("url", "")
    head = f'<a href="{_e(url)}">{title}</a>' if url else title
    pub = _e(s.get("publisher", "")) or "Wire"
    src = f'<a href="{_e(url)}" style="color:#6a6a6a">{pub}</a>' if url else pub
    summary = _e(s.get("summary", ""))
    sum_html = f'<p class="rsum">{summary}</p>' if summary else ""
    return (f'<div class="rstory"><div class="rh">{head}</div>'
            f'{sum_html}<span class="src">{src}</span></div>')


def _region_sub_full(label, stories):
    if stories:
        body = "".join(_region_story_full(s) for s in stories)
    else:
        body = '<p class="muted">No items this cycle.</p>'
    return f'<div class="rsub"><div class="rsublabel">{label}</div>{body}</div>'


def _regions_section(regions):
    """The complete regional desks for the WEB edition: every story shows its
    headline + summary inline so the page reads top-to-bottom with no click."""
    blocks = []
    for reg in regions:
        blocks.append(
            f'<div class="region"><div class="rname">{_e(reg["name"])}</div>'
            '<div class="rcols">'
            + _region_sub_full("Politics", reg.get("politics", []))
            + _region_sub_full("Macro &amp; Markets", reg.get("macro", []))
            + '</div></div>')
    return '<div class="sec">The Regional Desks</div>' + "".join(blocks)


def _overseas_section(overseas, headlines):
    ov = "".join(
        f'<div class="ovrow"><div>{_e(o["name"])} '
        f'<span class="src">{_e(o["region"])}</span></div>'
        f'<div>{_e(o["value"])} &nbsp; {_arrow(o["direction"])} {_e(o["change"])}</div></div>'
        for o in overseas)
    if headlines:
        hl = "".join(
            f'<div class="ovrow"><div><a href="{_e(h["url"])}" '
            f'style="color:#141414;text-decoration:none">{_e(h["title"])}</a> '
            f'<span class="src">{_e(h["publisher"])}</span></div></div>'
            for h in headlines[:12])
    else:
        hl = '<p class="muted">Overnight headlines connect when the feed returns.</p>'
    return ('<div class="sec">Overnight &amp; Overseas</div>'
            '<div class="ov"><div class="ovcol">'
            '<div class="ct">Overseas Closes</div>' + ov + '</div>'
            '<div class="ovcol"><div class="ct">Overnight Headlines</div>'
            + hl + '</div></div>')


def _calendar_section(cal):
    if not cal.get("connected"):
        return ('<div class="sec">The Day Ahead</div>'
                '<p class="muted">The forward calendar (economic prints and '
                'earnings) connects in the next setup step.</p>')
    econ = "".join(
        f'<tr><td>{_e(e["time"])}</td><td>{_e(e["event"])}</td>'
        f'<td class="r">{_e(e.get("consensus","-"))}</td>'
        f'<td class="r">{_e(e.get("prior","-"))}</td></tr>'
        for e in cal["economic"]) or '<tr><td class="muted">None scheduled.</td></tr>'
    earn = "".join(
        f'<tr><td><span class="tkr">{_e(x["ticker"])}</span> {_e(x.get("name",""))}</td>'
        f'<td class="r">{_e(x.get("time",""))}</td>'
        f'<td class="r">{_e(x.get("eps","-"))}</td></tr>'
        for x in cal["earnings"]) or '<tr><td class="muted">None scheduled.</td></tr>'
    return ('<div class="sec">The Day Ahead</div>'
            '<div class="cal"><div class="calcol"><div class="ct">Economic Releases (ET)</div>'
            f'<table class="c">{econ}</table></div>'
            '<div class="calcol"><div class="ct">Earnings</div>'
            f'<table class="c">{earn}</table></div></div>')


def render(edition, data, browser_url="", issue=None):
    tz = ZoneInfo(config.TIMEZONE)
    now = dt.datetime.now(tz)
    try:
        date_str = now.strftime("%A, %B %-d, %Y")
    except Exception:
        date_str = now.strftime("%A, %B %d, %Y")
    vol, num = _issue_parts(issue)
    edition_label = "Morning Edition" if edition == "morning" else "Evening Edition"
    compiled = now.strftime("%-I:%M %p CT") if _supports_dash() else now.strftime("%I:%M %p CT")

    browser_bar = ""
    if browser_url:
        browser_bar = (f'<div class="browserbar">Reading in your inbox? '
                       f'<a href="{_e(browser_url)}">View the full edition in your browser &rarr;</a></div>')

    parts = [browser_bar, '<div class="paper">',
             '<div class="toprule"></div>',
             f'<div class="flag">{_e(config.PAPER_NAME)}</div>',
             '<div class="meta">'
             f'<span>Vol. {vol} &middot; No. {num}</span>'
             f'<span>{_e(date_str)}</span>'
             f'<span>{_e(edition_label)}</span></div>',
             _strip_html(data["strip"]),
             _lead_html(data["headlines"])]

    if edition == "evening":
        parts.append(_movers_section(data["movers"], data["index_levels"]))
        parts.append(_sector_section(data["sector_desk"]))
        parts.append(_regions_section(data.get("regions", [])))
        parts.append(_calendar_section(data["calendar"]))
    else:
        parts.append(_overseas_section(data["overseas"], data["headlines"]))
        parts.append(_sector_section(data["sector_desk"]))
        parts.append(_regions_section(data.get("regions", [])))
        parts.append(_calendar_section(data["calendar"]))

    sources = ("Sources: Polygon (US movers, market &amp; sector news), Yahoo Finance "
               "(data strip, sector moves, overseas). Regional desks: The Guardian "
               "and The New York Times when keys are set.")
    parts.append(
        f'<div class="foot">{sources}<br>'
        f'{_e(config.PAPER_NAME)} &middot; Compiled {_e(compiled)} &middot; '
        f'Vol. {vol} &middot; No. {num}</div>')
    parts.append("</div>")

    body = "".join(parts)
    sr = (f'<h2 class="sr-only">{_e(config.PAPER_NAME)} {edition_label} for '
          f'{_e(date_str)}.</h2>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{_e(config.PAPER_NAME)} &middot; {edition_label}</title>'
            f'<style>{CSS}</style></head><body>{sr}{body}</body></html>')


def _supports_dash():
    try:
        dt.datetime.now().strftime("%-I")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Gmail-safe email rendering.
#
# Gmail strips <style> blocks, web fonts, and modern CSS (flexbox, multi-column,
# ::first-letter). render_email() produces the SAME content and layout as
# render(), but every style is inline, all layout is <table>-based, fonts fall
# back to Georgia, and the drop cap is replaced by a bold first paragraph.
# render() (the web edition) is left completely untouched.
# ---------------------------------------------------------------------------

_EFONT = "Georgia, 'Times New Roman', serif"
_EBG = "#FBFBF9"       # paper
_EINK = "#141414"      # ink
_ERULE = "#C7C7C7"     # hairline rule
_ERULE2 = "#E4E4E2"    # lighter hairline rule
_ESEC = "#5a5a5a"      # secondary text


def _etable(extra=""):
    """Opening tag for a presentation table with the Gmail-safe defaults."""
    style = "border-collapse:collapse;" + extra
    return (f'<table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" style="{style}">')


def _email_section(title):
    return (
        _etable("margin:22px 0 13px;") +
        f'<tr><td style="border-top:3px solid {_EINK};border-bottom:1px solid {_EINK};'
        f'padding:6px 0;text-align:center;font-family:{_EFONT};font-weight:bold;'
        f'font-size:13px;text-transform:uppercase;letter-spacing:3px;color:{_EINK};">'
        f'{title}</td></tr></table>')


def _email_strip(rows):
    if not rows:
        return ""
    per_row = 4
    trs = []
    for i in range(0, len(rows), per_row):
        tds = []
        for r in rows[i:i + per_row]:
            arrow = _arrow(r["direction"])
            chg = f'{arrow} {_e(r["change"])}' if r["change"] else ""
            tds.append(
                f'<td width="25%" valign="top" style="padding:6px 9px;'
                f'border-right:1px solid {_ERULE};border-top:1px solid {_ERULE};'
                f'font-family:{_EFONT};">'
                f'<div style="font-size:11px;text-transform:uppercase;'
                f'letter-spacing:.4px;color:{_ESEC};">{_e(r["label"])}</div>'
                f'<div style="font-size:15px;font-weight:bold;line-height:1.25;'
                f'color:{_EINK};">{_e(r["value"])}</div>'
                f'<div style="font-size:11px;color:{_EINK};">{chg}</div></td>')
        while len(tds) < per_row:
            tds.append(f'<td width="25%" style="border-top:1px solid {_ERULE};"></td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return (_etable(f"border-bottom:2px solid {_EINK};border-left:1px solid {_ERULE};"
                    "margin:14px 0 16px;") + "".join(trs) + "</table>")


def _email_lead(headlines):
    if headlines:
        top = headlines[0]
        title = _e(top["title"])
        link = top["url"]
        head = (f'<a href="{_e(link)}" style="color:{_EINK};text-decoration:none;">'
                f'{title}</a>') if link else title
        pub = _e(top["publisher"]) if top["publisher"] else "Wire"
        framing = ("The session's most prominent market story leads the page; "
                   "the desks below carry movers, sectors, and the day's schedule.")
    else:
        head = "Markets in Brief"
        pub = config.PAPER_NAME
        framing = ("Headlines connect once the market news feed returns for this "
                   "cycle. Movers, sectors, and the day ahead follow.")
    return (
        _etable() + f'<tr><td style="font-family:{_EFONT};">'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;'
        f'font-weight:bold;border-bottom:1px solid {_EINK};display:inline-block;'
        f'padding-bottom:2px;margin-bottom:7px;color:{_EINK};">Markets</div>'
        f'<div style="font-weight:bold;font-size:28px;line-height:1.08;'
        f'margin:1px 0 6px;color:{_EINK};">{head}</div>'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;'
        f'color:{_ESEC};margin-bottom:8px;">{pub}</div>'
        f'<div style="font-size:13px;line-height:1.5;color:{_EINK};">'
        f'<b>{framing}</b></div></td></tr></table>')


def _email_movers_table(rows):
    if not rows:
        return (_etable() + f'<tr><td style="font-family:{_EFONT};font-size:12px;'
                f'font-style:italic;color:#6a6a6a;">No qualifying names.</td></tr></table>')
    cell = (f"padding:2.5px 0;border-bottom:1px solid {_ERULE2};"
            f"font-family:{_EFONT};font-size:12px;")
    body = []
    for r in rows:
        name = _e(r.get("name", "")) or ""
        co = f' <span style="font-size:11px;color:{_ESEC};">{name}</span>' if name else ""
        body.append(
            f'<tr><td style="{cell}"><span style="font-weight:bold;">'
            f'{_e(r["ticker"])}</span>{co}</td>'
            f'<td align="right" style="{cell}white-space:nowrap;">{r["last"]:,.2f}</td>'
            f'<td align="right" style="{cell}white-space:nowrap;">{r["pct"]:+.1f}%</td></tr>')
    return _etable() + "".join(body) + "</table>"


def _email_cap(label, glyph):
    return (_etable() + '<tr>'
            f'<td style="font-family:{_EFONT};font-size:11px;text-transform:uppercase;'
            f'letter-spacing:1.2px;font-weight:bold;border-bottom:1px solid {_EINK};'
            f'padding-bottom:2px;color:{_EINK};">{label}</td>'
            f'<td align="right" style="border-bottom:1px solid {_EINK};'
            f'padding-bottom:2px;font-family:{_EFONT};">{glyph}</td></tr></table>')


def _email_movers_section(all_movers, index_levels):
    blocks = []
    any_data = False
    for idx in config.MOVERS_INDICES:
        data = all_movers.get(idx, {"winners": [], "losers": []})
        if data["winners"] or data["losers"]:
            any_data = True
        lvl = index_levels.get(idx, {})
        px = ""
        if lvl:
            arrow = _arrow(lvl.get("direction", "flat"))
            px = f'{_e(lvl.get("value",""))} &middot; {arrow} {_e(lvl.get("change",""))}'
        blocks.append(
            _etable("margin-bottom:16px;") +
            f'<tr><td style="font-family:{_EFONT};border-bottom:1.5px solid {_EINK};'
            f'padding-bottom:3px;font-weight:bold;font-size:15px;color:{_EINK};">'
            f'{_e(idx)}</td>'
            f'<td align="right" style="font-family:{_EFONT};border-bottom:1.5px solid '
            f'{_EINK};padding-bottom:3px;font-size:12px;color:{_EINK};">{px}</td></tr>'
            f'<tr><td colspan="2" style="padding-top:7px;">' +
            _etable() + '<tr>'
            f'<td width="50%" valign="top" style="padding-right:12px;">' +
            _email_cap("Winners", "▲") + _email_movers_table(data["winners"]) + '</td>'
            f'<td width="50%" valign="top" style="padding-left:12px;">' +
            _email_cap("Losers", "▼") + _email_movers_table(data["losers"]) + '</td>'
            '</tr></table></td></tr></table>')
    note = ""
    if not any_data:
        note = (f'<div style="font-family:{_EFONT};font-size:12px;font-style:italic;'
                f'color:#6a6a6a;margin-bottom:10px;">Movers populate once the '
                f'market-data feed returns two settled sessions for this run.</div>')
    return _email_section("The Close &middot; Biggest Movers") + note + "".join(blocks)


def _email_two_col(cells, pad="0 13px 13px 0"):
    """Lay a list of already-built <td>...</td>-less inner strings two per row."""
    trs = []
    for i in range(0, len(cells), 2):
        chunk = cells[i:i + 2]
        tds = [f'<td width="50%" valign="top" style="padding:{pad};">{c}</td>'
               for c in chunk]
        while len(tds) < 2:
            tds.append('<td width="50%"></td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return _etable() + "".join(trs) + "</table>"


def _email_sector_section(desk):
    cells = []
    for s in desk:
        arrow = _arrow(s["direction"])
        move = f'{arrow} {_e(s["move"])}' if s["move"] else ""
        if s["items"]:
            items = "".join(
                f'<p style="font-family:{_EFONT};font-size:12.5px;line-height:1.4;'
                f'margin:0 0 5px;color:{_EINK};">'
                f'<span style="font-weight:bold;">{_e(it["ticker"])}:</span> '
                f'<a href="{_e(it["url"])}" style="color:{_EINK};text-decoration:none;">'
                f'{_e(it["title"])}</a> '
                f'<span style="font-size:10.5px;color:#6a6a6a;">{_e(it["publisher"])}</span>'
                f'</p>' for it in s["items"])
        else:
            items = (f'<p style="font-family:{_EFONT};font-size:12px;font-style:italic;'
                     f'color:#6a6a6a;margin:0 0 5px;">No flagged single-stock '
                     f'headlines this cycle.</p>')
        cells.append(
            _etable("margin-bottom:5px;") + '<tr>'
            f'<td style="font-family:{_EFONT};font-weight:bold;font-size:15px;'
            f'border-bottom:1.5px solid {_EINK};padding-bottom:2px;color:{_EINK};">'
            f'{_e(s["name"])}</td>'
            f'<td align="right" style="font-family:{_EFONT};font-size:12px;'
            f'border-bottom:1.5px solid {_EINK};padding-bottom:2px;color:{_EINK};">'
            f'{move}</td></tr></table>' + items)
    body = _email_two_col(cells) if cells else ""
    return _email_section("The Sector Desk") + body


def _email_region_briefs(label, stories, browser_url):
    """A tight, headline-only briefs list for one desk sub-section. Each
    headline links to the full web edition (browser_url)."""
    lbl = (f'<div style="font-family:{_EFONT};font-size:10.5px;'
           f'text-transform:uppercase;letter-spacing:1.2px;font-weight:bold;'
           f'color:{_ESEC};margin:6px 0 3px;">{label}</div>')
    if not stories:
        return (lbl + f'<p style="font-family:{_EFONT};font-size:11.5px;'
                f'font-style:italic;color:#6a6a6a;margin:0 0 4px;">'
                f'No items this cycle.</p>')
    items = "".join(
        f'<div style="margin-bottom:3px;">'
        f'<a href="{_e(browser_url or s.get("url",""))}" '
        f'style="font-family:{_EFONT};font-size:12.5px;color:{_EINK};'
        f'text-decoration:none;">&bull; {_e(s.get("title",""))}</a> '
        f'<span style="font-family:{_EFONT};font-size:10px;color:#6a6a6a;">'
        f'{_e(s.get("publisher",""))}</span></div>' for s in stories)
    return lbl + items


def _email_regions_section(regions, browser_url):
    blocks = []
    for reg in regions:
        blocks.append(
            _etable("margin:0 0 4px;") + '<tr>'
            f'<td style="font-family:{_EFONT};font-weight:bold;font-size:15px;'
            f'border-bottom:1.5px solid {_EINK};padding-bottom:2px;color:{_EINK};">'
            f'{_e(reg["name"])}</td></tr></table>'
            + _email_region_briefs("Politics", reg.get("politics", []), browser_url)
            + _email_region_briefs("Macro & Markets", reg.get("macro", []), browser_url)
            + '<div style="height:10px;line-height:10px;">&nbsp;</div>')
    body = "".join(blocks)
    if browser_url:
        body += (f'<p style="font-family:{_EFONT};font-size:11px;font-style:italic;'
                 f'color:{_ESEC};margin:2px 0 0;">Each item opens the full edition '
                 f'&mdash; '
                 f'<a href="{_e(browser_url)}" style="color:{_ESEC};">read every '
                 f'story with its summary in your browser &rarr;</a></p>')
    return _email_section("The Regional Desks") + body


def render_email(edition, data, browser_url="", issue=None):
    """Gmail-safe, COMPACT twin of render(): masthead, full data strip, lead,
    movers (evening), sector moves, and headline-only regional briefs that link
    to the full web edition. All-inline styles, table layout, Georgia fonts."""
    tz = ZoneInfo(config.TIMEZONE)
    now = dt.datetime.now(tz)
    try:
        date_str = now.strftime("%A, %B %-d, %Y")
    except Exception:
        date_str = now.strftime("%A, %B %d, %Y")
    vol, num = _issue_parts(issue)
    edition_label = "Morning Edition" if edition == "morning" else "Evening Edition"
    compiled = now.strftime("%-I:%M %p CT") if _supports_dash() else now.strftime("%I:%M %p CT")

    browser_bar = ""
    if browser_url:
        browser_bar = (
            _etable("max-width:700px;margin:0 auto 10px;") +
            f'<tr><td align="center" style="font-family:{_EFONT};font-size:12px;'
            f'letter-spacing:.5px;color:#333;">Reading in your inbox? '
            f'<a href="{_e(browser_url)}" style="color:#333;text-decoration:underline;">'
            f'View the full edition in your browser &rarr;</a></td></tr></table>')

    meta_td = (f'font-family:{_EFONT};font-size:11px;text-transform:uppercase;'
               f'letter-spacing:1px;padding:6px 2px;color:{_EINK};')
    masthead = (
        _etable() +
        f'<tr><td style="border-top:3px solid {_EINK};padding-top:12px;"></td></tr>'
        f'<tr><td align="center" style="font-family:{_EFONT};font-weight:bold;'
        f'font-size:46px;letter-spacing:1px;text-transform:uppercase;line-height:1.02;'
        f'color:{_EINK};">{_e(config.PAPER_NAME)}</td></tr></table>'
        + _etable(f"border-top:2px solid {_EINK};border-bottom:1px solid {_EINK};"
                  "margin-top:12px;") + '<tr>'
        f'<td align="left" style="{meta_td}">Vol. {vol} &middot; No. {num}</td>'
        f'<td align="center" style="{meta_td}">{_e(date_str)}</td>'
        f'<td align="right" style="{meta_td}">{_e(edition_label)}</td></tr></table>')

    parts = [masthead, _email_strip(data["strip"]),
             _email_lead(data["headlines"])]
    if edition == "evening":
        parts.append(_email_movers_section(data["movers"], data["index_levels"]))
    parts.append(_email_sector_section(data["sector_desk"]))
    parts.append(_email_regions_section(data.get("regions", []), browser_url))

    sources = ("Sources: Polygon (US movers, market &amp; sector news), Yahoo Finance "
               "(data strip, sector moves). Regional desks: The Guardian and The "
               "New York Times when keys are set.")
    parts.append(
        _etable(f"border-top:2px solid {_EINK};margin-top:20px;") +
        f'<tr><td align="center" style="font-family:{_EFONT};font-size:11px;'
        f'color:#3a3a3a;line-height:1.45;padding-top:8px;">{sources}<br>'
        f'{_e(config.PAPER_NAME)} &middot; Compiled {_e(compiled)} &middot; '
        f'Vol. {vol} &middot; No. {num}</td></tr></table>')

    inner = "".join(parts)
    paper = (
        _etable(f"max-width:700px;margin:0 auto;background:{_EBG};") +
        f'<tr><td style="padding:30px 34px 24px;background:{_EBG};">{inner}</td>'
        f'</tr></table>')

    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_e(config.PAPER_NAME)} &middot; {edition_label}</title></head>'
        f'<body style="margin:0;padding:18px;background:#e9e9e6;">'
        f'{browser_bar}{paper}</body></html>')
