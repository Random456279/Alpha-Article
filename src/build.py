"""
Main entry point. Run as:  python -m src.build --edition evening
or                          python -m src.build --edition morning

Gathers data, renders The River Report, writes the browser edition into docs/
(served by GitHub Pages), and emails it to you. Designed so that a single
failing data source never stops the edition from going out.
"""

import argparse
import datetime as dt
import json
import os
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, datasources as ds, render, emailer

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "archive"

# Persisted, repo-committed issue counter. Numbering starts at Vol. 1, No. 1 for
# the first edition published on or after ISSUE_EPOCH and advances by one for
# every edition sent (morning and evening each advance it). No. rolls 1..100,
# then the volume increments and No. resets to 1.
COUNTER = DOCS / "issue_counter.json"
ISSUE_EPOCH = dt.date(2026, 6, 24)
ISSUES_PER_VOLUME = 100


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        traceback.print_exc()
        return default


def _pages_base_url():
    repo = os.environ.get("GITHUB_REPOSITORY", "")  # "owner/name"
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return ""


def _index_levels(strip_rows):
    out = {}
    for r in strip_rows:
        if r["label"] in config.MOVERS_INDICES:
            out[r["label"]] = {"value": r["value"], "change": r["change"],
                               "direction": r["direction"]}
    return out


def assign_issue(edition, today):
    """Return {"volume", "number"} for this edition, advancing and persisting the
    committed counter. Re-running the same date+edition does not double-count.
    Numbering only begins on/after ISSUE_EPOCH."""
    key = f"{today.isoformat()}-{edition}"
    try:
        c = json.loads(COUNTER.read_text(encoding="utf-8"))
    except Exception:
        c = None

    # Already counted this exact edition (a re-run): reuse, do not advance.
    if c and c.get("last_edition_key") == key:
        return {"volume": c["volume"], "number": c["number"]}

    started = bool(c and c.get("number"))  # any issue published yet?

    # Before launch with nothing published: show 1/1 but don't consume it.
    if today < ISSUE_EPOCH and not started:
        return {"volume": 1, "number": 1}

    if not started:
        vol, num = 1, 1
    else:
        vol, num = c["volume"], c["number"] + 1
        if num > ISSUES_PER_VOLUME:
            vol, num = vol + 1, 1

    DOCS.mkdir(exist_ok=True)
    COUNTER.write_text(json.dumps(
        {"epoch": ISSUE_EPOCH.isoformat(), "volume": vol, "number": num,
         "last_edition_key": key}, indent=2) + "\n", encoding="utf-8")
    return {"volume": vol, "number": num}


def gather(edition):
    strip_cfg = config.EVENING_STRIP if edition == "evening" else config.MORNING_STRIP
    strip = _safe(lambda: ds.get_strip(strip_cfg), [])
    data = {
        "strip": strip,
        "headlines": _safe(lambda: ds.get_market_headlines(), []),
        "sector_desk": _safe(lambda: ds.get_sector_desk(), []),
        "regions": _safe(lambda: ds.get_regional_desks(), []),
        "calendar": _safe(lambda: ds.get_calendar(), {"economic": [], "earnings": [], "connected": False}),
    }
    if edition == "evening":
        data["movers"] = _safe(lambda: ds.get_all_movers(), {})
        data["index_levels"] = _index_levels(strip)
    else:
        data["overseas"] = _safe(lambda: ds.get_overseas(), [])
    return data


def time_gate_ok(edition):
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        return True  # manual "Run workflow" always sends, for testing
    now = dt.datetime.now(ZoneInfo(config.TIMEZONE))
    target = config.MORNING_HOUR if edition == "morning" else config.EVENING_HOUR
    return now.hour == target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", choices=["morning", "evening"], required=True)
    ap.add_argument("--no-email", action="store_true",
                    help="render and write the page but do not send mail")
    args = ap.parse_args()

    if not time_gate_ok(args.edition):
        now = dt.datetime.now(ZoneInfo(config.TIMEZONE))
        print(f"Outside the {args.edition} send window "
              f"(Central time is {now.strftime('%H:%M')}). Skipping.")
        return 0

    print(f"Building the {args.edition} edition...")
    data = gather(args.edition)

    base = _pages_base_url()
    now = dt.datetime.now(ZoneInfo(config.TIMEZONE))
    archive_name = f"{now.date().isoformat()}-{args.edition}.html"
    browser_url = (base + f"archive/{archive_name}") if base else ""

    issue = assign_issue(args.edition, now.date())
    print(f"Issue: Vol. {issue['volume']} No. {issue['number']}")

    html_out = render.render(args.edition, data, browser_url=browser_url, issue=issue)

    DOCS.mkdir(exist_ok=True)
    ARCHIVE.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html_out, encoding="utf-8")
    (ARCHIVE / archive_name).write_text(html_out, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Wrote docs/index.html and docs/archive/{archive_name}")

    if args.no_email:
        print("Skipping email (--no-email).")
        return 0

    edition_label = "Morning Edition" if args.edition == "morning" else "Evening Edition"
    date_str = now.strftime("%B %d, %Y")
    subject = f"{config.PAPER_NAME}: {edition_label}, {date_str}"
    # The web edition (docs/index.html + archive) uses render.render() above.
    # Gmail strips <style>/web fonts/modern CSS, so the email body uses the
    # inline, table-based render.render_email() twin instead.
    email_html = render.render_email(args.edition, data, browser_url=browser_url, issue=issue)
    try:
        sent_to = emailer.send_email(subject, email_html)
        print(f"Emailed the {args.edition} edition to {sent_to}.")
    except Exception:
        traceback.print_exc()
        print("Email step failed (the web edition still wrote successfully).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
