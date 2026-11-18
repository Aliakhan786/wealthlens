"""Extract step: pull raw data from free sources (yfinance, mfapi.in) with an offline fallback.

Every fetcher returns a DataFrame indexed by date with columns open/high/low/close/volume.
"""
from __future__ import annotations

import logging
import zlib
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

from pipeline.assets import HELPER_SYMBOLS, TROY_OUNCE_GRAMS, AssetDef

log = logging.getLogger("wealthlens.fetch")
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "WealthLens/1.0 (educational project)"})
OHLC = ["open", "high", "low", "close", "volume"]


# ----------------------------------------------------------------------------- yfinance
def fetch_yahoo(symbol: str, start: date) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(symbol, start=start.isoformat(), progress=False, auto_adjust=True, threads=False)
    if df is None or df.empty:
        raise ValueError(f"No data from Yahoo for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):  # yfinance >= 0.2.40 returns (field, ticker)
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    df = df[[c for c in OHLC if c in df.columns]]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def fetch_yahoo_quote(symbol: str) -> tuple[float, float | None]:
    """Latest (delayed) price and previous close using 5 days of 1-minute-ish data."""
    import yfinance as yf

    t = yf.Ticker(symbol)
    hist = t.history(period="5d", interval="5m", auto_adjust=True)
    daily = t.history(period="10d", interval="1d", auto_adjust=True)
    if hist.empty and daily.empty:
        raise ValueError(f"No quote for {symbol}")
    price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else float(daily["Close"].iloc[-1])
    prev = None
    if len(daily) >= 2:
        last_day = daily.index[-1].date()
        today_bar = hist.index[-1].date() if not hist.empty else last_day
        prev = float(daily["Close"].iloc[-2] if today_bar == last_day else daily["Close"].iloc[-1])
    return price, prev


# ----------------------------------------------------------------------------- mfapi.in
def fetch_mf(scheme_code: str, start: date) -> pd.DataFrame:
    r = HTTP.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=30)
    r.raise_for_status()
    rows = r.json().get("data", [])
    if not rows:
        raise ValueError(f"No NAV data for scheme {scheme_code}")
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["close"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["close"]).set_index("date").sort_index()[["close"]]
    df = df[df.index >= pd.Timestamp(start)]
    for c in ("open", "high", "low"):
        df[c] = df["close"]
    df["volume"] = np.nan
    return df[OHLC]


# ----------------------------------------------------------------------------- derived (gold/silver in INR)
def fetch_metal_inr(metal: str, start: date) -> pd.DataFrame:
    usd = fetch_yahoo(HELPER_SYMBOLS[f"{metal}_usd"], start)
    fx = fetch_yahoo(HELPER_SYMBOLS["usdinr"], start)["close"]
    fx = fx.reindex(usd.index.union(fx.index)).ffill().reindex(usd.index)
    grams = 10 if metal == "gold" else 1000
    factor = fx * grams / TROY_OUNCE_GRAMS
    out = usd[["open", "high", "low", "close"]].mul(factor, axis=0)
    out["volume"] = usd.get("volume")
    return out.dropna(subset=["close"])


# ----------------------------------------------------------------------------- offline fallback
SYNTH_PARAMS = {  # (start price, annual drift, annual vol) — roughly realistic, clearly labelled as sample data
    "commodity": (8000, 0.11, 0.16), "etf": (10, 0.11, 0.16), "index": (6000, 0.12, 0.20),
    "fx": (45, 0.03, 0.06), "mutual_fund": (10, 0.13, 0.19),
}


def synthetic_series(asset: AssetDef, start: date, end: date | None = None) -> pd.DataFrame:
    """Geometric Brownian motion with a regime-switching crash, seeded per asset (deterministic)."""
    end = end or date.today()
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(zlib.crc32(asset.id.encode()))
    p0, mu, sigma = SYNTH_PARAMS.get(asset.asset_class, (100, 0.1, 0.18))
    dt = 1 / 252
    shocks = rng.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), len(idx))
    # Inject a couple of drawdown regimes so dip analytics have something to show
    for crash_at in rng.choice(len(idx), size=max(1, len(idx) // 1500), replace=False):
        shocks[crash_at : crash_at + 60] -= 0.004
    close = p0 * np.exp(np.cumsum(shocks))
    df = pd.DataFrame(index=idx, data={"close": close})
    noise = np.abs(rng.normal(0, sigma * np.sqrt(dt) / 2, len(idx)))
    df["open"] = df["close"].shift(1).fillna(p0)
    df["high"] = df[["open", "close"]].max(axis=1) * (1 + noise)
    df["low"] = df[["open", "close"]].min(axis=1) * (1 - noise)
    df["volume"] = np.nan
    return df[OHLC]


def fetch_asset_history(asset: AssetDef, years: int, offline: bool = False) -> tuple[pd.DataFrame, bool]:
    """Return (dataframe, is_synthetic)."""
    start = date.today() - timedelta(days=int(years * 365.25))
    if not offline:
        try:
            if asset.source == "mfapi":
                return fetch_mf(asset.symbol, start), False
            if asset.source == "derived":
                return fetch_metal_inr(asset.id, start), False
            return fetch_yahoo(asset.symbol, start), False
        except Exception as e:  # network down, symbol delisted, rate-limited…
            log.warning("Falling back to sample data for %s: %s", asset.id, e)
    return synthetic_series(asset, start), True
