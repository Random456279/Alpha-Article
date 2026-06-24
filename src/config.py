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

# Polygon's news firehose is mostly PR-wire spam, paid-promotion pieces, and
# class-action "investor alert" filings. We keep ONLY articles whose publisher
# name contains one of these (case-insensitive substring; "ap" is matched as a
# whole word so it doesn't swallow unrelated names). This drops Motley Fool,
# Zacks, GlobeNewswire, PR Newswire, Business Wire, Benzinga-PR, etc.
NEWS_PUBLISHER_ALLOWLIST = [
    "reuters", "associated press", "ap", "cnbc", "marketwatch", "barron",
    "bloomberg", "wall street journal", "financial times", "forbes",
    "investor's business daily", "yahoo finance",
]

# Drop any headline whose title contains one of these spam markers (the
# law-firm "shareholder rights / class action / deadline" boilerplate).
NEWS_TITLE_BLOCKLIST = [
    "class action", "lawsuit", "investor alert", "deadline", "law firm",
    "shareholder rights", "reminds investors", "encourages investors",
    "investigation on behalf", "to recover losses", "rosen law", "pomerantz",
    "bragar", "halper sadeh", "schall law",
]

# Term sets used to split each regional desk into Politics vs Macro & Markets.
NEWS_MACRO_TERMS = [
    "econom", "market", "stock", "shares", "bond", "yield", "inflation",
    "interest rate", "central bank", "gdp", "currency", "tariff", "trade",
    "earnings", "ipo", "investor", "budget", "deficit", "fiscal", "monetary",
    "commodit", "recession", "unemployment", "jobs report", "rate cut",
    "rate hike", "dollar", "equit", "fed", "ecb", "boj", "pboc",
]
NEWS_POLITICS_TERMS = [
    "politic", "election", "government", "parliament", "president",
    "prime minister", "minister", "congress", "senate", "vote", "diploma",
    "sanction", "military", "troops", "summit", "protest", "coup", "cabinet",
    "legislat", "border", "immigration", "war",
]

# Six regional desks, in display order. Each desk renders two sub-sections,
# "Politics" and "Macro & Markets". Stories are pulled in bulk from The Guardian
# and the NYT, then assigned to EXACTLY ONE desk by strict keyword matching (see
# datasources.get_regional_desks). No story may appear in more than one desk.
REGION_ORDER = [
    "Washington", "Europe & U.K.", "China", "Japan", "South America",
    "The Rest of the World",
]

# Per-region keyword sets used for that strict assignment.
#   specific : a named country / capital / institution (match weight 2)
#   generic  : a broad regional term that a more specific match should beat (1)
#   priority : tie-break when two regions match at the SAME weight; lower wins.
#              Foreign-specific desks outrank Washington so a globally-relevant
#              "US" mention can't pull a foreign story into Washington.
# "The Rest of the World" is BOTH a keyword desk (Middle East, Africa, South
# Asia, Oceania, Korea, etc.) AND the catch-all for stories matching nothing.
# NOTE: Korea/North Korea live here, NOT under China. The U.K. lives under
# Europe, never anywhere else.
REGION_KEYWORDS = {
    "Washington": {
        "priority": 6,
        "specific": [
            "washington", "white house", "congress", "senate", "federal reserve",
            "wall street", "biden", "trump", "sec", "treasury",
            # US states (Georgia omitted: it collides with the country)
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
            "connecticut", "delaware", "florida", "hawaii", "idaho", "illinois",
            "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
            "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
            "missouri", "montana", "nebraska", "nevada", "new hampshire",
            "new jersey", "new mexico", "new york", "north carolina",
            "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
            "rhode island", "south carolina", "south dakota", "tennessee",
            "texas", "utah", "vermont", "virginia", "west virginia",
            "wisconsin", "wyoming",
        ],
        "generic": ["united states", "u.s.", "us", "fed", "republican",
                    "democrat", "gop"],
    },
    "Europe & U.K.": {
        "priority": 3,
        "specific": [
            "united kingdom", "u.k.", "uk", "britain", "british", "england",
            "scotland", "wales", "london", "brexit", "ecb", "germany", "france",
            "italy", "spain", "netherlands", "brussels", "european union",
            "ukraine", "russia", "poland", "greece", "ireland", "berlin",
            "paris", "madrid", "rome", "moscow", "kyiv", "labour", "tory",
            "downing street",
        ],
        "generic": ["europe", "european", "eurozone", "eu"],
    },
    "China": {
        "priority": 1,
        "specific": [
            "china", "chinese", "beijing", "shanghai", "shenzhen", "hong kong",
            "xi jinping", "taiwan", "taipei", "pboc", "hang seng", "csi 300",
        ],
        "generic": ["yuan", "renminbi"],
    },
    "Japan": {
        "priority": 2,
        "specific": [
            "japan", "japanese", "tokyo", "nikkei", "boj", "bank of japan",
            "yen", "topix",
        ],
        "generic": [],
    },
    "South America": {
        "priority": 4,
        "specific": [
            "brazil", "brazilian", "argentina", "argentine", "chile", "colombia",
            "peru", "venezuela", "bolivia", "uruguay", "paraguay", "ecuador",
            "brasilia", "sao paulo", "buenos aires", "santiago", "bogota",
            "lima", "caracas", "lula", "milei", "petro",
        ],
        "generic": ["south america", "latin america", "mercosur"],
    },
    "The Rest of the World": {
        "priority": 5,
        "specific": [
            "india", "indian", "mumbai", "delhi", "middle east", "iran",
            "tehran", "israel", "israeli", "gaza", "palestin", "saudi",
            "riyadh", "uae", "united arab emirates", "dubai", "abu dhabi",
            "qatar", "africa", "nigeria", "south africa", "johannesburg",
            "kenya", "egypt", "cairo", "turkey", "ankara", "istanbul",
            "australia", "australian", "sydney", "new zealand", "korea",
            "north korea", "south korea", "seoul", "pyongyang", "pakistan",
            "indonesia", "vietnam", "thailand", "singapore", "philippines",
            "malaysia", "antarctica",
        ],
        "generic": [],
    },
}

# ---------------------------------------------------------------------------
# Forward calendar ("The Day Ahead"). Free, keyless sources.
# ---------------------------------------------------------------------------
# Notable companies to list in the earnings calendar (most by market cap).
CAL_EARNINGS_N = 12
# Economic releases to list (today + tomorrow, US).
CAL_ECON_N = 14
