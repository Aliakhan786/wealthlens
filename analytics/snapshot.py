"""Pre-computed metrics bundle stored in `metrics_snapshot` — nothing heavy runs per API request."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from analytics import metrics as m
from analytics.dips import dip_analysis


def period_inflation(macro: pd.DataFrame | None, start: pd.Timestamp, end: pd.Timestamp, col: str) -> float | None:
    """Geometric average of a yearly % series (CPI or FD) over the years covered."""
    if macro is None or macro.empty:
        return None
    years = macro[(macro["year"] >= start.year) & (macro["year"] <= end.year)]
    if years.empty:
        return None
    growth = np.prod(1 + years[col].values / 100)
    return float(growth ** (1 / len(years)) - 1)


def compute_snapshot(close: pd.Series, macro: pd.DataFrame | None = None) -> dict[str, Any]:
    s = m.to_series(close)
    vol = m.annualized_volatility(s)
    cagr_all = m.cagr(s)
    infl = period_inflation(macro, s.index[0], s.index[-1], "cpi_inflation")
    fd = period_inflation(macro, s.index[0], s.index[-1], "fd_rate")
    yearly = m.period_returns(s, "YE")
    dips = {f"{int(t*100)}": dip_analysis(s, t) for t in (0.10, 0.20)}
    for d in dips.values():
        d.pop("events")  # events served on demand by /dip-history; keep the snapshot small

    snap = {
        "start_date": s.index[0],
        "end_date": s.index[-1],
        "latest_price": float(s.iloc[-1]),
        "years_of_data": round(m.years_between(s.index[0], s.index[-1]), 1),
        "trailing": m.trailing_returns(s),
        "cagr_since_start": cagr_all,
        "volatility": vol,
        "risk_label": m.risk_label(vol),
        "max_drawdown": m.max_drawdown(s),
        "current_drawdown": float(m.drawdown_series(s).iloc[-1]),
        "drawdown_episodes_10": len(m.drawdown_episodes(s, 0.10)),
        **m.best_worst_days(s),
        "streaks": m.streaks(s),
        "yearly_returns": [{"year": d.year, "return": float(v)} for d, v in yearly.items()],
        "rolling": {f"{y}y": m.rolling_summary(s, y) for y in (1, 3, 5)},
        "benchmarks": {
            "avg_inflation": infl,
            "avg_fd_rate": fd,
            "real_cagr": m.real_return(cagr_all, infl),
            "excess_over_fd": (cagr_all - fd) if (cagr_all is not None and fd is not None) else None,
        },
        "dips": dips,
    }
    return m.to_jsonable(snap)
