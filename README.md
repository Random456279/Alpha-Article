# The Alpha Article

A twice-daily, black-and-white, WSJ-style markets newspaper that emails itself to
you and publishes a full browser edition. Runs entirely on GitHub's servers, free.

- **Morning Edition** — 7:00 AM CT: futures, overnight macro, overseas closes, the
  Sector Desk, and the day ahead.
- **Evening Edition** — 4:30 PM CT: the close, the biggest movers across the
  S&P 500, Nasdaq 100, Dow 30, and Russell 2000, the Sector Desk, and more.

## How it runs

Two scheduled GitHub Actions (`.github/workflows/morning.yml` and `evening.yml`)
wake up on a cron timer, run `python -m src.build`, email you the edition, and
publish the browser version into `docs/` (served by GitHub Pages). No computer of
yours needs to be on.

## Your keys (stored as repository Secrets, never in the code)

| Secret | What it is | Needed for |
| --- | --- | --- |
| `POLYGON_API_KEY` | Polygon.io key | Movers and market news |
| `GMAIL_USER` | your Gmail address | Sending the email |
| `GMAIL_APP_PASSWORD` | 16-char Gmail app password | Sending the email |
| `GUARDIAN_API_KEY` | The Guardian key (free) | World / political desks |
| `FRED_API_KEY` | FRED key (free, optional) | Treasury yields |
| `NYT_API_KEY` | NYT key (free, optional) | Extra world coverage |

The Guardian, FRED, and NYT keys are optional. Without them the paper still ships;
those sections show a short "activates when the key is added" note.

## Run it by hand

In the **Actions** tab, choose **Morning Edition** or **Evening Edition**, then
**Run workflow**. A manual run always sends, regardless of the time of day.

## Tweaking it

Almost everything you'd want to change (the masthead, the strip instruments, the
sector tickers) is in `src/config.py`. The look lives in `src/render.py`.
