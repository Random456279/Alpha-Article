"""
Central configuration for The River Report.

Everything you might want to tweak (the masthead name, the instruments shown in
the data strip, which tickers feed each sector, send times) lives here so you
never have to dig through the logic files.
"""

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
PAPER_NAME = "The River Report"

# ---------------------------------------------------------------------------
# Timing (US Central). The schedulers fire in UTC and the code gates on the
# real Central-time hour so it stays correct through daylight-saving changes.
# ---------------------------------------------------------------------------
TIMEZONE = "America/Chicago"
MORNING_HOUR = 7      # 7:00 AM CT
EVENING_HOUR = 16     # 4:30 PM CT (gate on the hour, the :30 is in the cron)

# ---------------------------------------------------------------------------
# Data-strip instruments, by edition. Rendered as exactly 4 rows of 4 cells:
#   Row 1: headline indices  (cash in the evening, futures in the morning)
#   Row 2: international      (STOXX Europe 600, FTSE 100, Nikkei 225, MSCI EM)
#   Row 3: rates & FX         (10-Year, 2-Year, Dollar, Euro)
#   Row 4: commodities/crypto (Gold, Silver, WTI Crude, Bitcoin)
# Each entry: (label, yahoo_symbol). yfinance needs no API key. The 2-year has no
# clean Yahoo cash-yield index; "2YY=F" is the CBOT 2-Year micro-yield future,
# and get_strip() falls back to "n/a" gracefully if it ever stops resolving.
# ---------------------------------------------------------------------------
EVENING_STRIP = [
    ("S&P 500", "^GSPC"),
    ("Nasdaq 100", "^NDX"),
    ("Dow 30", "^DJI"),
    ("Russell 2000", "^RUT"),
    ("STOXX Europe 600", "^STOXX"),
    ("FTSE 100", "^FTSE"),
    ("Nikkei 225", "^N225"),
    ("MSCI EM (EEM)", "EEM"),
    ("10-Year", "^TNX"),
    ("2-Year", "2YY=F"),
    ("Dollar (DXY)", "DX-Y.NYB"),
    ("Euro", "EURUSD=X"),
    ("Gold", "GC=F"),
    ("Silver", "SI=F"),
    ("WTI Crude", "CL=F"),
    ("Bitcoin", "BTC-USD"),
]

MORNING_STRIP = [
    ("S&P Fut", "ES=F"),
    ("Nasdaq Fut", "NQ=F"),
    ("Dow Fut", "YM=F"),
    ("Russell Fut", "RTY=F"),
    ("STOXX Europe 600", "^STOXX"),
    ("FTSE 100", "^FTSE"),
    ("Nikkei 225", "^N225"),
    ("MSCI EM (EEM)", "EEM"),
    ("10-Year", "^TNX"),
    ("2-Year", "2YY=F"),
    ("Dollar (DXY)", "DX-Y.NYB"),
    ("Euro", "EURUSD=X"),
    ("Gold", "GC=F"),
    ("Silver", "SI=F"),
    ("WTI Crude", "CL=F"),
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
# Sector Desk. Ten sectors, in this fixed display order (renders as two clean
# columns of five). For each: a display name, the SPDR ETF(s) whose day's move
# is shown, and a short list of bellwether tickers whose Polygon news feeds the
# section. "Consumer" merges Consumer Discretionary (XLY) and Consumer Staples
# (XLP); its move is the average of the two ETFs' percent moves -- pass the ETF
# field as a tuple and get_sector_moves() averages it.
# ---------------------------------------------------------------------------
SECTORS = [
    ("Technology",             "XLK",          ["NVDA", "AAPL", "MSFT", "AVGO", "AMD", "ORCL"]),
    ("Financials",             "XLF",          ["JPM", "BAC", "WFC", "GS", "MS", "V"]),
    ("Health Care",            "XLV",          ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"]),
    ("Consumer",               ("XLY", "XLP"), ["AMZN", "TSLA", "HD", "MCD", "PG", "KO", "PEP", "COST"]),
    ("Communication Services", "XLC",          ["GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ"]),
    ("Industrials",            "XLI",          ["CAT", "BA", "GE", "HON", "UPS", "RTX"]),
    ("Energy",                 "XLE",          ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"]),
    ("Materials",              "XLB",          ["LIN", "SHW", "FCX", "NEM", "APD", "DOW"]),
    ("Utilities",              "XLU",          ["NEE", "SO", "DUK", "CEG", "AEP", "D"]),
    ("Real Estate",            "XLRE",         ["PLD", "AMT", "EQIX", "SPG", "O", "WELL"]),
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
# How many headlines to show per news block / per regional sub-section.
NEWS_PER_BLOCK = 4

# Six regional desks, in display order. Each desk renders two sub-sections,
# "Politics" and "Macro & Markets", populated from The Guardian and the NYT
# (keys in env vars GUARDIAN_API_KEY / NYT_API_KEY; empty -> desks degrade to a
# "No items this cycle" note). For each desk:
#   guardian.politics / guardian.macro : Guardian section slugs to pull from
#   query                              : keyword filter (Guardian q= and NYT q=)
#                                        narrowing the desk to its region
# "The Rest of the World" is the catch-all for everything the five named desks
# do not cover (Middle East, Africa, Central/South Asia, Oceania, Antarctica).
REGIONAL_DESKS = [
    {"name": "Washington",
     "guardian": {"politics": "us-news", "macro": "business"},
     "query": "United States"},
    {"name": "Europe & U.K.",
     "guardian": {"politics": "politics", "macro": "business"},
     "query": "Europe OR \"United Kingdom\" OR Britain OR eurozone"},
    {"name": "China",
     "guardian": {"politics": "world", "macro": "business"},
     "query": "China OR Beijing OR Hong Kong"},
    {"name": "Japan",
     "guardian": {"politics": "world", "macro": "business"},
     "query": "Japan OR Tokyo OR \"Bank of Japan\""},
    {"name": "South America",
     "guardian": {"politics": "world", "macro": "business"},
     "query": "\"South America\" OR Brazil OR Argentina OR Chile OR Colombia OR Peru"},
    {"name": "The Rest of the World",
     "guardian": {"politics": "world", "macro": "business"},
     "query": ("\"Middle East\" OR Africa OR India OR Pakistan OR Australia "
               "OR Oceania OR \"Central Asia\"")},
]
