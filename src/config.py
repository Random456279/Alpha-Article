"""
Central configuration for The Alpha Article.

Everything you might want to tweak (the masthead name, the instruments shown in
the data strip, which tickers feed each sector, send times) lives here so you
never have to dig through the logic files.
"""

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
PAPER_NAME = "The Alpha Article"
MOTTO = "The Day's Edge, Open to Close"

# ---------------------------------------------------------------------------
# Timing (US Central). The schedulers fire in UTC and the code gates on the
# real Central-time hour so it stays correct through daylight-saving changes.
# ---------------------------------------------------------------------------
TIMEZONE = "America/Chicago"
MORNING_HOUR = 7      # 7:00 AM CT
EVENING_HOUR = 16     # 4:30 PM CT (gate on the hour, the :30 is in the cron)

# ---------------------------------------------------------------------------
# Data-strip instruments, by edition.
# Each entry: (label, yahoo_symbol). yfinance needs no API key.
# ---------------------------------------------------------------------------
EVENING_STRIP = [
    ("S&P 500", "^GSPC"),
    ("Nasdaq 100", "^NDX"),
    ("Dow 30", "^DJI"),
    ("Russell 2000", "^RUT"),
    ("VIX", "^VIX"),
    ("10-Yr", "^TNX"),
    ("Dollar (DXY)", "DX-Y.NYB"),
    ("WTI Crude", "CL=F"),
    ("Gold", "GC=F"),
    ("Bitcoin", "BTC-USD"),
]

MORNING_STRIP = [
    ("S&P Fut", "ES=F"),
    ("Nasdaq Fut", "NQ=F"),
    ("Dow Fut", "YM=F"),
    ("Russell Fut", "RTY=F"),
    ("10-Yr", "^TNX"),
    ("Dollar (DXY)", "DX-Y.NYB"),
    ("Yen (USD/JPY)", "JPY=X"),
    ("WTI Crude", "CL=F"),
    ("Gold", "GC=F"),
    ("Bitcoin", "BTC-USD"),
]

# Overseas index closes shown in the morning edition.
OVERSEAS = [
    ("Nikkei 225", "Tokyo", "^N225"),
    ("Hang Seng", "Hong Kong", "^HSI"),
    ("Shanghai Comp", "China", "000001.SS"),
    ("DAX", "Germany", "^GDAXI"),
    ("FTSE 100", "U.K.", "^FTSE"),
    ("CAC 40", "France", "^FCHI"),
    ("Stoxx 600", "Europe", "^STOXX"),
]

# ---------------------------------------------------------------------------
# Sector Desk. For each sector: a display name, the sector SPDR ETF used to
# show the day's move, and a short list of bellwether tickers whose news feeds
# the section. Real Estate is intentionally last.
# ---------------------------------------------------------------------------
SECTORS = [
    ("Technology",        "XLK",  ["NVDA", "AAPL", "MSFT", "AVGO", "AMD", "ORCL"]),
    ("Financials",        "XLF",  ["JPM", "BAC", "GS", "MS", "V", "MA"]),
    ("Health Care",       "XLV",  ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"]),
    ("Consumer & Retail", "XLY",  ["AMZN", "TSLA", "HD", "NKE", "MCD", "COST"]),
    ("Industrials",       "XLI",  ["CAT", "BA", "GE", "HON", "UPS", "DE"]),
    ("Energy",            "XLE",  ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"]),
    ("Real Estate",       "XLRE", ["PLD", "AMT", "EQIX", "SPG", "O", "WELL"]),
]

# ---------------------------------------------------------------------------
# Index membership for the movers tables. These are fetched live at run time
# (Wikipedia for the big three, the iShares IWM holdings file for the Russell
# 2000) with the small fallbacks below if a fetch ever fails, so the tables
# always populate with something sensible.
# ---------------------------------------------------------------------------
MOVERS_INDICES = ["S&P 500", "Nasdaq 100", "Dow 30", "Russell 2000"]

DOW30_FALLBACK = [
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "GS",
    "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT",
    "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT", "AMZN",
]

# How many winners / losers to show per index in each table.
TOP_N = 10

# Minimum dollar price for a stock to qualify as a mover (filters out the
# penny-stock noise that otherwise dominates raw percentage moves).
MIN_PRICE = 3.0

# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------
# Guardian sections pulled for the world / political desks (used once the free
# Guardian key is added). Empty handling is automatic.
GUARDIAN_SECTIONS = ["us-news", "world", "politics", "business"]

# How many headlines to show per news block.
NEWS_PER_BLOCK = 4
