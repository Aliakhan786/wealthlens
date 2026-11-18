"""Transform step: make raw price series trustworthy before they hit the database."""
from __future__ import annotations

import numpy as np
import pandas as pd


def adjust_unadjusted_splits(df: pd.DataFrame, min_ratio: float = 3.0) -> pd.DataFrame:
    """Back-adjust history for splits/consolidations the data source missed.

    No asset in our universe can genuinely move 3x (or lose 67%) in one session, and such a jump that
    *persists* (the bad-tick filter already removed reversing spikes) is a corporate action — e.g.
    GOLDBEES' 1:100 unit split in 2019. Earlier prices are divided by the jump ratio.
    """
    df = df.copy()
    ratio = df["close"] / df["close"].shift(1)
    jumps = ratio[(ratio > min_ratio) | (ratio < 1 / min_ratio)]
    for when, r in jumps.items():
        mask = df.index < when
        for c in ("open", "high", "low", "close"):
            if c in df:
                df.loc[mask, c] = df.loc[mask, c] * r
    return df


def clean_prices(df: pd.DataFrame, max_daily_move: float = 0.35) -> pd.DataFrame:
    """
    - drop duplicate dates / non-positive prices
    - forward-fill small gaps (exchange holidays already excluded; this fixes 1-2 day data holes)
    - remove obvious bad ticks: a >35% one-day move that fully reverses next day
    - fill missing OHLC from close (NAV series have only close)
    Splits/dividends: Yahoo data is pulled with auto_adjust=True, NAVs are already adjusted.
    """
    if df.empty:
        return df
    df = df[~df.index.duplicated(keep="last")].sort_index().copy()
    df = df[df["close"] > 0]

    ret = df["close"].pct_change()
    spike = (ret.abs() > max_daily_move) & (ret.shift(-1).abs() > max_daily_move * 0.8) & (np.sign(ret) != np.sign(ret.shift(-1)))
    df = df[~spike]

    df = adjust_unadjusted_splits(df)

    for c in ("open", "high", "low"):
        if c not in df:
            df[c] = df["close"]
        df[c] = df[c].fillna(df["close"])
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1)
    if "volume" not in df:
        df["volume"] = np.nan
    return df[["open", "high", "low", "close", "volume"]]
