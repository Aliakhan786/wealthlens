"""The curated asset universe (18 assets). Keeping it focused beats tracking 5,000 tickers badly."""
from __future__ import annotations

from dataclasses import dataclass, field

TROY_OUNCE_GRAMS = 31.1034768


@dataclass(frozen=True)
class AssetDef:
    id: str
    name: str
    asset_class: str
    source: str  # yfinance | mfapi | derived
    symbol: str
    unit: str = "INR"
    description: str = ""
    keywords: tuple[str, ...] = field(default_factory=tuple)  # used to tag news


ASSETS: list[AssetDef] = [
    # ---- Commodities (derived: international USD price × USD/INR) ----
    AssetDef("gold", "Gold (₹ per 10g)", "commodity", "derived", "GC=F*USDINR",
             "INR / 10g", "International gold price converted to rupees per 10 grams (excludes import duty & GST).",
             ("gold", "bullion", "yellow metal")),
    AssetDef("silver", "Silver (₹ per kg)", "commodity", "derived", "SI=F*USDINR",
             "INR / kg", "International silver price converted to rupees per kilogram (excludes duties).",
             ("silver",)),
    AssetDef("goldbees", "Nippon Gold ETF (GOLDBEES)", "etf", "yfinance", "GOLDBEES.NS",
             "INR / unit", "Exchange-traded gold fund listed on NSE. Lets you own gold in your demat account.",
             ("goldbees", "gold etf")),
    # ---- Indices ----
    AssetDef("nifty50", "Nifty 50", "index", "yfinance", "^NSEI", "points",
             "India's 50 largest listed companies on the NSE.", ("nifty", "nifty 50", "stock market", "sensex", "equities")),
    AssetDef("sensex", "BSE Sensex", "index", "yfinance", "^BSESN", "points",
             "30 large, established companies listed on the BSE.", ("sensex", "bse", "stock market")),
    AssetDef("niftybank", "Nifty Bank", "index", "yfinance", "^NSEBANK", "points",
             "The most liquid large Indian banking stocks.", ("bank nifty", "banking", "banks", "rbi", "hdfc bank", "icici")),
    AssetDef("niftyit", "Nifty IT", "index", "yfinance", "^CNXIT", "points",
             "India's major IT services companies.", ("nifty it", "it stocks", "infosys", "tcs", "wipro", "tech")),
    AssetDef("usdinr", "USD / INR", "fx", "yfinance", "USDINR=X", "INR per USD",
             "How many rupees one US dollar buys. Rising = rupee weakening.", ("rupee", "dollar", "usd/inr", "forex")),
    # ---- Mutual funds (NAV from mfapi.in, Direct-Growth plans) ----
    AssetDef("uti-nifty50", "UTI Nifty 50 Index Fund", "mutual_fund", "mfapi", "120716", "NAV",
             "Low-cost passive fund that tracks the Nifty 50.", ("index fund", "nifty")),
    AssetDef("ppfas-flexi", "Parag Parikh Flexi Cap Fund", "mutual_fund", "mfapi", "122639", "NAV",
             "Flexi-cap fund that can invest across company sizes, including some global stocks.", ("flexi cap", "parag parikh")),
    AssetDef("hdfc-midcap", "HDFC Mid Cap Fund", "mutual_fund", "mfapi", "118989", "NAV",
             "Invests mainly in mid-sized Indian companies.", ("mid cap", "midcap")),
    AssetDef("sbi-smallcap", "SBI Small Cap Fund", "mutual_fund", "mfapi", "125497", "NAV",
             "Invests mainly in small companies: higher growth potential, bigger swings.", ("small cap", "smallcap")),
    AssetDef("nippon-smallcap", "Nippon India Small Cap Fund", "mutual_fund", "mfapi", "118778", "NAV",
             "One of India's largest small-cap funds.", ("small cap", "smallcap")),
    AssetDef("axis-elss", "Axis ELSS Tax Saver Fund", "mutual_fund", "mfapi", "120503", "NAV",
             "Equity-linked savings scheme: tax deduction under Sec 80C with a 3-year lock-in.", ("elss", "tax saver")),
    AssetDef("sbi-largecap", "SBI Large Cap Fund", "mutual_fund", "mfapi", "119598", "NAV",
             "Actively managed fund investing in large established companies.", ("large cap", "bluechip")),
    AssetDef("icici-largecap", "ICICI Prudential Large Cap Fund", "mutual_fund", "mfapi", "120586", "NAV",
             "Actively managed large-cap fund (formerly Bluechip Fund).", ("large cap", "bluechip")),
    AssetDef("mirae-largemid", "Mirae Asset Large & Midcap Fund", "mutual_fund", "mfapi", "118834", "NAV",
             "Mix of large and mid-sized companies.", ("large & midcap", "mirae")),
    AssetDef("motilal-midcap150", "Motilal Oswal Nifty Midcap 150 Index", "mutual_fund", "mfapi", "147622", "NAV",
             "Passive fund tracking 150 mid-sized companies.", ("midcap 150", "mid cap", "index fund")),
]

ASSET_BY_ID = {a.id: a for a in ASSETS}

# Raw Yahoo symbols that are needed only to derive other series.
HELPER_SYMBOLS = {"gold_usd": "GC=F", "silver_usd": "SI=F", "usdinr": "USDINR=X"}
