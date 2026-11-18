"""What-if simulators: SIP vs lump sum (with XIRR), and benchmarks (FD, inflation)."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

import pandas as pd

from analytics.metrics import value_on_or_before


def xirr(cashflows: Iterable[tuple[date, float]], lo: float = -0.9999, hi: float = 10.0) -> float | None:
    """Annualised internal rate of return for irregular cash flows (investments negative, value positive).

    Uses bisection — slower than Newton but never diverges, which matters for user-driven inputs.
    """
    flows = sorted((pd.Timestamp(d), float(a)) for d, a in cashflows)
    if len(flows) < 2 or not any(a > 0 for _, a in flows) or not any(a < 0 for _, a in flows):
        return None
    t0 = flows[0][0]

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** ((d - t0).days / 365.0) for d, a in flows)

    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-7:
            break
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def _month_starts(s: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    """First trading day of each month within [start, end]."""
    window = s.loc[start:end]
    if window.empty:
        return []
    return list(window.groupby([window.index.year, window.index.month]).head(1).index)


def simulate_sip(s: pd.Series, monthly: float, start: date, end: date | None = None,
                 step_up_pct: float = 0.0) -> dict[str, Any]:
    """Invest `monthly` on the first trading day of every month; optionally step up the amount yearly."""
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end) if end else s.index[-1]
    dates = _month_starts(s, start_ts, end_ts)
    if not dates:
        raise ValueError("No price data in the selected period")
    units = invested = 0.0
    flows: list[tuple[date, float]] = []
    path = []
    amount = monthly
    for i, d in enumerate(dates):
        if i and i % 12 == 0 and step_up_pct:
            amount *= 1 + step_up_pct / 100
        price = float(s.loc[d])
        units += amount / price
        invested += amount
        flows.append((d, -amount))
        path.append({"date": d, "invested": invested, "value": units * price})
    final_date, final_price = value_on_or_before(s, end_ts) or (s.index[-1], float(s.iloc[-1]))
    final_value = units * final_price
    path.append({"date": final_date, "invested": invested, "value": final_value})
    flows.append((final_date, final_value))
    return {
        "mode": "sip",
        "installments": len(dates),
        "invested": invested,
        "final_value": final_value,
        "gain": final_value - invested,
        "absolute_return": final_value / invested - 1,
        "xirr": xirr(flows),
        "path": path,
        "start": dates[0],
        "end": final_date,
    }


def simulate_lumpsum(s: pd.Series, amount: float, start: date, end: date | None = None) -> dict[str, Any]:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end) if end else s.index[-1]
    window = s.loc[start_ts:end_ts]
    if window.empty:
        raise ValueError("No price data in the selected period")
    p0 = float(window.iloc[0])
    units = amount / p0
    monthly = window.groupby([window.index.year, window.index.month]).tail(1)
    path = [{"date": window.index[0], "invested": amount, "value": amount}]
    path += [{"date": d, "invested": amount, "value": units * float(v)} for d, v in monthly.items()]
    final_value = units * float(window.iloc[-1])
    yrs = (window.index[-1] - window.index[0]).days / 365.25
    return {
        "mode": "lumpsum",
        "invested": amount,
        "final_value": final_value,
        "gain": final_value - amount,
        "absolute_return": final_value / amount - 1,
        "cagr": (final_value / amount) ** (1 / yrs) - 1 if yrs > 0.25 else None,
        "xirr": xirr([(window.index[0], -amount), (window.index[-1], final_value)]),
        "path": path,
        "start": window.index[0],
        "end": window.index[-1],
    }


def benchmark_path(path: list[dict[str, Any]], annual_rate_by_year: dict[int, float]) -> list[dict[str, Any]]:
    """Grow the same contributions at a yearly-varying rate (e.g. FD rate or CPI inflation).

    `path` is the output of a simulator; contributions are inferred from increases in `invested`.
    Rates are in percent. Missing years use the nearest known year.
    """
    if not path:
        return []
    known = sorted(annual_rate_by_year)

    def rate_for(year: int) -> float:
        if year in annual_rate_by_year:
            return annual_rate_by_year[year] / 100
        nearest = min(known, key=lambda y: abs(y - year))
        return annual_rate_by_year[nearest] / 100

    out, balance, prev_invested = [], 0.0, 0.0
    prev_date = pd.Timestamp(path[0]["date"])
    for p in path:
        d = pd.Timestamp(p["date"])
        days = (d - prev_date).days
        if days > 0:
            balance *= (1 + rate_for(d.year)) ** (days / 365.25)
        balance += p["invested"] - prev_invested
        prev_invested = p["invested"]
        prev_date = d
        out.append({"date": d, "value": balance})
    return out
