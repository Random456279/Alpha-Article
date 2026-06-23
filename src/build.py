"""
Main entry point. Run as:  python -m src.build --edition evening
or                          python -m src.build --edition morning

Gathers data, renders the Alpha Article, writes the browser edition into docs/
(served by GitHub Pages), and emails it to you. Designed so that a single
failing data source never stops the edition from going out.
"""

import argparse
import datetime as dt
import os
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, datasources as ds, render, emailer

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "archive"


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


def _world_desks():
    return [
        ("U.S. Politics", _safe(lambda: ds.get_guardian_section("us-news"), [])),
        ("U.S. Macro & Markets", _safe(lambda: ds.get_guardian_section("business"), [])),
        ("Global Politics", _safe(lambda: ds.get_guardian_section("world"), [])),
        ("Europe & U.K.", _safe(lambda: ds.get_guardian_section("politics"), [])),
    ]


def gather(edition):
    strip_cfg = config.EVENING_STRIP if edition == "evening" else config.MORNING_STRIP
    strip = _safe(lambda: ds.get_strip(strip_cfg), [])
    data = {
        "strip": strip,
        "headlines": _safe(lambda: ds.get_market_headlines(), []),
        "sector_desk": _safe(lambda: ds.get_sector_desk(), []),
        "world": _world_desks(),
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

    html_out = render.render(args.edition, data, browser_url=browser_url)

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
    try:
        sent_to = emailer.send_email(subject, html_out)
        print(f"Emailed the {args.edition} edition to {sent_to}.")
    except Exception:
        traceback.print_exc()
        print("Email step failed (the web edition still wrote successfully).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
