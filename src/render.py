"""
Renders the full Alpha Article page (used as both the email body and the
GitHub Pages web edition). Black-and-white WSJ-style broadsheet, serif type,
hairline rules, tabular figures. Same look you signed off on in the mockups.
"""

import datetime as dt
import html
from zoneinfo import ZoneInfo

from . import config

_ISSUE_EPOCH = dt.date(2026, 6, 1)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=PT+Serif:ital,wght@0,400;0,700;1,400&display=swap');
body{margin:0;background:#e9e9e6;padding:18px}
.paper{max-width:760px;margin:0 auto;box-sizing:border-box;background:#FBFBF9;color:#141414;padding:30px 34px 24px;font-family:'PT Serif',Georgia,serif;line-height:1.45;border:1px solid #DcDcD8;font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}
.paper *{box-sizing:border-box}
.browserbar{max-width:760px;margin:0 auto 10px;text-align:center;font-family:'PT Serif',Georgia,serif;font-size:12px;letter-spacing:.5px}
.browserbar a{color:#333;text-decoration:underline}
.toprule{border-top:3px solid #141414;margin-bottom:12px}
.flag{font-family:'Playfair Display',Georgia,serif;font-weight:900;font-size:46px;letter-spacing:1px;text-transform:uppercase;text-align:center;line-height:1.02}
.motto{text-align:center;font-style:italic;font-size:14px;letter-spacing:.3px;color:#3a3a3a;margin-top:7px}
.meta{display:flex;justify-content:space-between;font-size:11px;text-transform:uppercase;letter-spacing:1px;padding:6px 2px;border-top:2px solid #141414;border-bottom:1px solid #141414;margin-top:12px}
.strip{display:flex;flex-wrap:wrap;border-bottom:2px solid #141414;border-left:1px solid #C7C7C7;margin:14px 0 16px}
.q{flex:1 1 92px;min-width:92px;padding:6px 9px;border-right:1px solid #C7C7C7;border-top:1px solid #C7C7C7}
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
        '<div class="dateline">The Alpha Article</div>'
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


def _news_block(label, items):
    if items:
        inner = "".join(
            f'<div class="art"><div class="k">{_e(label)}</div>'
            f'<h3><a href="{_e(it["url"])}">{_e(it["title"])}</a></h3>'
            f'<span class="src">{_e(it.get("publisher",""))}</span></div>'
            for it in items)
        return inner
    return (f'<div class="art"><div class="k">{_e(label)}</div>'
            f'<p class="muted">This desk activates when the free Guardian key '
            f'is added (next step).</p></div>')


def _world_section(world):
    blocks = "".join(_news_block(lbl, items) for lbl, items in world)
    return ('<div class="sec">The World &amp; Washington</div>'
            '<div class="news">' + blocks + "</div>")


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
            for h in headlines[:6])
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


def render(edition, data, browser_url=""):
    tz = ZoneInfo(config.TIMEZONE)
    now = dt.datetime.now(tz)
    date_str = now.strftime("%A, %B %-d, %Y") if hasattr(now, "strftime") else str(now.date())
    try:
        date_str = now.strftime("%A, %B %-d, %Y")
    except Exception:
        date_str = now.strftime("%A, %B %d, %Y")
    issue_no = (now.date() - _ISSUE_EPOCH).days + 1
    edition_label = "Morning Edition" if edition == "morning" else "Evening Edition"
    compiled = now.strftime("%-I:%M %p CT") if _supports_dash() else now.strftime("%I:%M %p CT")

    browser_bar = ""
    if browser_url:
        browser_bar = (f'<div class="browserbar">Reading in your inbox? '
                       f'<a href="{_e(browser_url)}">View the full edition in your browser &rarr;</a></div>')

    parts = [browser_bar, '<div class="paper">',
             '<div class="toprule"></div>',
             f'<div class="flag">{_e(config.PAPER_NAME)}</div>',
             f'<div class="motto">&ldquo;{_e(config.MOTTO)}&rdquo;</div>',
             '<div class="meta">'
             f'<span>Vol. I &middot; No. {issue_no}</span>'
             f'<span>{_e(date_str)}</span>'
             f'<span>{_e(edition_label)}</span></div>',
             _strip_html(data["strip"]),
             _lead_html(data["headlines"])]

    if edition == "evening":
        parts.append(_movers_section(data["movers"], data["index_levels"]))
        parts.append(_sector_section(data["sector_desk"]))
        parts.append(_world_section(data["world"]))
        parts.append(_calendar_section(data["calendar"]))
    else:
        parts.append(_overseas_section(data["overseas"], data["headlines"]))
        parts.append(_sector_section(data["sector_desk"]))
        parts.append(_world_section(data["world"]))
        parts.append(_calendar_section(data["calendar"]))

    sources = ("Sources: Polygon (movers, market news), Yahoo Finance (indices, "
               "futures, overseas, sectors). World desk: The Guardian when enabled.")
    parts.append(
        f'<div class="foot">{sources}<br>'
        f'{_e(config.PAPER_NAME)} &middot; Compiled {_e(compiled)} &middot; '
        f'Issue No. {issue_no}</div>')
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
