"""⭐ History-based dip analyzer.

"When this asset fell X% from its peak, what happened 1/3/5 years later?"
Facts about the past only — no predictions.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from analytics.metrics import value_on_or_before


def find_dip_events(s: pd.Series, threshold: float = 0.10) -> list[dict[str, Any]]:
    """One event per drawdown episode: the first day the price closes `threshold` below its running peak.

    The detector re-arms only after a new all-time high, so a single long crash counts once.
    """
    events = []
    peak_val, peak_date, armed = float(s.iloc[0]), s.index[0], True
    for d, v in s.items():
        v = float(v)
        if v >= peak_val:
            peak_val, peak_date, armed = v, d, True
            continue
        dd = v / peak_val - 1
        if armed and dd <= -threshold:
            events.append({"date": d, "price": v, "peak_date": peak_date, "peak_price": peak_val, "drawdown": dd})
            armed = False
    return events


def dip_analysis(s: pd.Series, threshold: float = 0.10, horizons: tuple[int, ...] = (1, 3, 5)) -> dict[str, Any]:
    events = find_dip_events(s, threshold)
    last_date = s.index[-1]
    for e in events:
        e["forward"] = {}
        for h in horizons:
            target = e["date"] + pd.DateOffset(years=h)
            if target > last_date:
                e["forward"][f"{h}y"] = None
                continue
            _, fv = value_on_or_before(s, target)
            e["forward"][f"{h}y"] = fv / e["price"] - 1
        # how long until the old peak was reclaimed
        after = s.loc[e["date"]:]
        rec = after[after >= e["peak_price"]]
        e["recovered_on"] = rec.index[0] if not rec.empty else None
        e["days_to_recover"] = int((rec.index[0] - e["date"]).days) if not rec.empty else None

    summary = {}
    for h in horizons:
        vals = [e["forward"][f"{h}y"] for e in events if e["forward"].get(f"{h}y") is not None]
        if not vals:
            summary[f"{h}y"] = None
            continue
        sv = pd.Series(vals)
        summary[f"{h}y"] = {
            "observations": len(vals),
            "win_rate": float((sv > 0).mean()),
            "avg_return": float(sv.mean()),
            "median_return": float(sv.median()),
            "best": float(sv.max()),
            "worst": float(sv.min()),
        }

    peak = float(s.cummax().iloc[-1])
    current_dd = float(s.iloc[-1]) / peak - 1
    recovered_days = [e["days_to_recover"] for e in events if e["days_to_recover"] is not None]
    return {
        "threshold": threshold,
        "events": events,
        "summary": summary,
        "event_count": len(events),
        "avg_days_to_recover": float(pd.Series(recovered_days).mean()) if recovered_days else None,
        "current_drawdown": current_dd,
        "currently_in_dip": current_dd <= -threshold,
    }
