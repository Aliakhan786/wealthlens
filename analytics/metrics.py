"""Core return / risk metrics. Pure functions over a pandas Series of prices indexed by date."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

TRADING_DAYS = 252
TRAILING_PERIODS = {"1M": 1 / 12, "3M": 0.25, "6M": 0.5, "1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10, "15Y": 15, "20Y": 20}


def to_series(close: pd.Series) -> pd.Series:
    s = pd.Series(close, dtype="float64").dropna()
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()


def years_between(a: pd.Timestamp, b: pd.Timestamp) -> float:
    return (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25


def daily_returns(s: pd.Series) -> pd.Series:
    return s.pct_change().dropna()


def period_returns(s: pd.Series, freq: str = "YE") -> pd.Series:
    """Calendar-period returns. freq: 'ME' monthly, 'YE' yearly. First (partial) period measured from first price."""
    ends = s.resample(freq).last().dropna()
    prev = ends.shift(1)
    prev.iloc[0] = s.iloc[0]
    return (ends / prev - 1).dropna()


def cagr(s: pd.Series) -> float | None:
    if len(s) < 2:
        return None
    yrs = years_between(s.index[0], s.index[-1])
    if yrs <= 0:
        return None
    return float((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1)


def value_on_or_before(s: pd.Series, when: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    pos = s.index.searchsorted(pd.Timestamp(when), side="right") - 1
    if pos < 0:
        return None
    return s.index[pos], float(s.iloc[pos])


def trailing_returns(s: pd.Series) -> dict[str, dict[str, float] | None]:
    """Absolute return for every window, plus annualised (CAGR) for windows ≥ 1 year."""
    out: dict[str, dict[str, float] | None] = {}
    end_date, end_val = s.index[-1], float(s.iloc[-1])
    for label, yrs in TRAILING_PERIODS.items():
        start = end_date - pd.DateOffset(days=int(round(yrs * 365.25)))
        if start < s.index[0] - pd.Timedelta(days=7):
            out[label] = None
            continue
        hit = value_on_or_before(s, start) or (s.index[0], float(s.iloc[0]))
        absolute = end_val / hit[1] - 1
        out[label] = {"absolute": absolute, "cagr": (1 + absolute) ** (1 / yrs) - 1 if yrs >= 1 else None}
    return out


def rolling_cagr(s: pd.Series, years: int) -> pd.Series:
    """CAGR of every `years`-long holding period ending on each date."""
    past_dates = s.index - pd.DateOffset(years=years)
    pos = s.index.searchsorted(past_dates, side="right") - 1
    valid = pos >= 0
    # require the window to actually start inside the data (not before the first price)
    valid &= past_dates >= s.index[0]
    past_vals = np.where(valid, s.values[np.clip(pos, 0, None)], np.nan)
    out = (s.values / past_vals) ** (1 / years) - 1
    return pd.Series(out, index=s.index).dropna()


def rolling_summary(s: pd.Series, years: int) -> dict[str, Any] | None:
    r = rolling_cagr(s, years)
    if r.empty:
        return None
    return {
        "years": years,
        "observations": int(len(r)),
        "min": float(r.min()),
        "median": float(r.median()),
        "max": float(r.max()),
        "pct_positive": float((r > 0).mean()),
        "pct_above_7": float((r > 0.07).mean()),
    }


def annualized_volatility(s: pd.Series) -> float | None:
    r = daily_returns(s)
    if len(r) < 20:
        return None
    return float(r.std() * math.sqrt(TRADING_DAYS))


def risk_label(vol: float | None) -> str | None:
    """Volatility buckets (annualised std-dev of daily returns)."""
    if vol is None:
        return None
    if vol < 0.10:
        return "Low"
    if vol < 0.21:
        return "Medium"
    return "High"


def drawdown_series(s: pd.Series) -> pd.Series:
    return s / s.cummax() - 1


def max_drawdown(s: pd.Series) -> dict[str, Any] | None:
    """Deepest peak-to-trough fall and how long it took to get back to the old peak."""
    if len(s) < 2:
        return None
    dd = drawdown_series(s)
    trough = dd.idxmin()
    depth = float(dd.loc[trough])
    if depth >= 0:
        return {"depth": 0.0, "peak_date": None, "trough_date": None, "recovery_date": None,
                "days_to_recover": None, "recovered": True}
    peak = s.loc[:trough].idxmax()
    after = s.loc[trough:]
    rec = after[after >= s.loc[peak]]
    recovery = rec.index[0] if not rec.empty else None
    return {
        "depth": depth,
        "peak_date": peak,
        "trough_date": trough,
        "recovery_date": recovery,
        "days_to_recover": int((recovery - trough).days) if recovery is not None else None,
        "months_peak_to_recovery": round((recovery - peak).days / 30.44, 1) if recovery is not None else None,
        "recovered": recovery is not None,
    }


def drawdown_episodes(s: pd.Series, min_depth: float = 0.10) -> list[dict[str, Any]]:
    """Every distinct fall of at least `min_depth` from an all-time high, with its recovery."""
    episodes: list[dict[str, Any]] = []
    peak_date, peak_val = s.index[0], float(s.iloc[0])
    trough_date, trough_val = peak_date, peak_val
    for d, v in s.items():
        v = float(v)
        if v >= peak_val:
            if trough_val / peak_val - 1 <= -min_depth:
                episodes.append({"peak_date": peak_date, "trough_date": trough_date, "recovery_date": d,
                                 "depth": trough_val / peak_val - 1,
                                 "days_to_recover": (d - trough_date).days})
            peak_date, peak_val, trough_date, trough_val = d, v, d, v
        elif v < trough_val:
            trough_date, trough_val = d, v
    if trough_val / peak_val - 1 <= -min_depth:
        episodes.append({"peak_date": peak_date, "trough_date": trough_date, "recovery_date": None,
                         "depth": trough_val / peak_val - 1, "days_to_recover": None})
    return episodes


def best_worst_days(s: pd.Series) -> dict[str, Any]:
    r = daily_returns(s)
    if r.empty:
        return {}
    return {"best_day": {"date": r.idxmax(), "return": float(r.max())},
            "worst_day": {"date": r.idxmin(), "return": float(r.min())},
            "pct_positive_days": float((r > 0).mean())}


def streaks(s: pd.Series) -> dict[str, Any]:
    """Longest run of consecutive up days and down days."""
    r = daily_returns(s)
    best = {"up": (0, None, None), "down": (0, None, None)}
    cur_kind, cur_len, cur_start = None, 0, None
    for d, v in r.items():
        kind = "up" if v > 0 else "down" if v < 0 else None
        if kind and kind == cur_kind:
            cur_len += 1
        else:
            cur_kind, cur_len, cur_start = kind, (1 if kind else 0), d
        if kind and cur_len > best[kind][0]:
            best[kind] = (cur_len, cur_start, d)
    return {k: {"days": v[0], "start": v[1], "end": v[2]} for k, v in best.items()}


def real_return(nominal: float | None, inflation: float | None) -> float | None:
    if nominal is None or inflation is None:
        return None
    return (1 + nominal) / (1 + inflation) - 1


def to_jsonable(obj: Any) -> Any:
    """Convert numpy / pandas types (and NaN) into plain JSON values."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.date().isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if math.isnan(f) or math.isinf(f) else round(f, 6)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj
