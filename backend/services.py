"""Read-side business logic shared by the REST routers and the AI agent's tools."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select

from analytics import metrics as m
from analytics.dips import dip_analysis
from analytics.simulators import benchmark_path, simulate_lumpsum, simulate_sip
from backend.cache import cached
from core.db import Asset, Macro, MetricsSnapshot, PriceDaily, PriceLive, session_scope


class NotFound(Exception):
    pass


# ------------------------------------------------------------------ series cache (process-local)
_SERIES: dict[str, tuple[float, pd.DataFrame]] = {}
SERIES_TTL = 120


def ohlc_frame(asset_id: str) -> pd.DataFrame:
    hit = _SERIES.get(asset_id)
    if hit and hit[0] > time.time():
        return hit[1]
    with session_scope() as s:
        rows = s.execute(select(PriceDaily.date, PriceDaily.open, PriceDaily.high, PriceDaily.low, PriceDaily.close)
                         .where(PriceDaily.asset_id == asset_id).order_by(PriceDaily.date)).all()
    if not rows:
        raise NotFound(asset_id)
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    _SERIES[asset_id] = (time.time() + SERIES_TTL, df)
    return df


def close_series(asset_id: str) -> pd.Series:
    return ohlc_frame(asset_id)["close"]


def macro_rates() -> tuple[dict[int, float], dict[int, float]]:
    with session_scope() as s:
        rows = s.execute(select(Macro)).scalars().all()
    return {r.year: r.fd_rate for r in rows}, {r.year: r.cpi_inflation for r in rows}


def _snapshot(asset_id: str) -> dict[str, Any] | None:
    with session_scope() as s:
        snap = s.get(MetricsSnapshot, asset_id)
        return snap.payload if snap else None


def _asset_row(a: Asset) -> dict[str, Any]:
    return {"id": a.id, "name": a.name, "asset_class": a.asset_class, "symbol": a.symbol, "unit": a.unit,
            "description": a.description, "risk": a.risk_category, "is_sample_data": a.is_synthetic,
            "first_date": a.first_date.isoformat() if a.first_date else None,
            "last_date": a.last_date.isoformat() if a.last_date else None}


# ------------------------------------------------------------------ assets
@cached("assets", ttl=60)
def list_assets() -> list[dict[str, Any]]:
    with session_scope() as s:
        assets = s.execute(select(Asset).order_by(Asset.asset_class, Asset.name)).scalars().all()
        live = {p.asset_id: p for p in s.execute(select(PriceLive)).scalars().all()}
        snaps = {x.asset_id: x.payload for x in s.execute(select(MetricsSnapshot)).scalars().all()}
    out = []
    for a in assets:
        row = _asset_row(a)
        snap = snaps.get(a.id) or {}
        lp = live.get(a.id)
        tr = snap.get("trailing", {})
        row.update({
            "price": lp.price if lp else snap.get("latest_price"),
            "change_pct": lp.change_pct if lp else None,
            "price_ts": lp.ts.isoformat() if lp else None,
            "return_1y": (tr.get("1Y") or {}).get("absolute"),
            "cagr_5y": (tr.get("5Y") or {}).get("cagr"),
            "cagr_10y": (tr.get("10Y") or {}).get("cagr"),
            "volatility": snap.get("volatility"),
            "max_drawdown": (snap.get("max_drawdown") or {}).get("depth"),
            "sparkline": sparkline(a.id),
        })
        out.append(row)
    return out


def sparkline(asset_id: str, points: int = 60) -> list[float]:
    try:
        s = close_series(asset_id).iloc[-180:]
    except NotFound:
        return []
    step = max(1, len(s) // points)
    return [round(float(v), 4) for v in s.iloc[::step]]


def get_asset(asset_id: str) -> dict[str, Any]:
    with session_scope() as s:
        a = s.get(Asset, asset_id)
        if not a:
            raise NotFound(asset_id)
        lp = s.get(PriceLive, asset_id)
        row = _asset_row(a)
    row["live"] = {"price": lp.price, "change": lp.change, "change_pct": lp.change_pct, "ts": lp.ts.isoformat()} if lp else None
    return row


RANGES = {"1M": 31, "6M": 183, "1Y": 366, "3Y": 3 * 366, "5Y": 5 * 366, "10Y": 10 * 366, "MAX": None}


@cached("prices", ttl=300)
def get_prices(asset_id: str, range_: str = "1Y") -> dict[str, Any]:
    df = ohlc_frame(asset_id)
    days = RANGES.get(range_.upper(), 366)
    if days:
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=days)]
    weekly = len(df) > 1300
    if weekly:  # weekly candles for long ranges keeps payloads small
        df = df.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    ma50 = df["close"].rolling(50).mean()
    ma200 = df["close"].rolling(200).mean()
    candles = [{"time": d.strftime("%Y-%m-%d"), "open": round(r.open, 4), "high": round(r.high, 4),
                "low": round(r.low, 4), "close": round(r.close, 4)} for d, r in df.iterrows()]
    return {
        "asset_id": asset_id, "range": range_.upper(), "interval": "1w" if weekly else "1d",
        "candles": candles,
        "ma50": [{"time": d.strftime("%Y-%m-%d"), "value": round(v, 4)} for d, v in ma50.dropna().items()],
        "ma200": [{"time": d.strftime("%Y-%m-%d"), "value": round(v, 4)} for d, v in ma200.dropna().items()],
        "change": float(df["close"].iloc[-1] / df["close"].iloc[0] - 1) if len(df) > 1 else 0.0,
    }


def get_metrics(asset_id: str) -> dict[str, Any]:
    snap = _snapshot(asset_id)
    if snap is None:
        raise NotFound(asset_id)
    s = close_series(asset_id)
    recent = {}
    for label, days in (("1W", 7), ("1M", 30)):
        hit = m.value_on_or_before(s, s.index[-1] - pd.Timedelta(days=days))
        recent[label] = float(s.iloc[-1] / hit[1] - 1) if hit else None
    return {**snap, "recent": recent}


@cached("calendar", ttl=600)
def get_calendar(asset_id: str, year: int | None = None) -> dict[str, Any]:
    s = close_series(asset_id)
    r = m.daily_returns(s)
    year = year or int(r.index[-1].year)
    yr = r[r.index.year == year]
    monthly = m.period_returns(s, "ME")
    return {
        "asset_id": asset_id, "year": year,
        "years_available": sorted({int(y) for y in r.index.year}, reverse=True),
        "days": [{"date": d.strftime("%Y-%m-%d"), "return": round(float(v), 6)} for d, v in yr.items()],
        "monthly": [{"year": int(d.year), "month": int(d.month), "return": round(float(v), 6)} for d, v in monthly.items()],
    }


@cached("drawdown", ttl=600)
def get_drawdown(asset_id: str) -> dict[str, Any]:
    s = close_series(asset_id)
    dd = m.drawdown_series(s)
    step = max(1, len(dd) // 800)
    pts = dd.iloc[::step]
    episodes = m.drawdown_episodes(s, 0.10)
    return {"asset_id": asset_id,
            "series": [{"date": d.strftime("%Y-%m-%d"), "drawdown": round(float(v), 5)} for d, v in pts.items()],
            "episodes": m.to_jsonable(sorted(episodes, key=lambda e: e["depth"])[:8])}


@cached("dips", ttl=600)
def get_dip_history(asset_id: str, threshold: float = 0.10) -> dict[str, Any]:
    s = close_series(asset_id)
    res = dip_analysis(s, threshold)
    return m.to_jsonable(res)


# ------------------------------------------------------------------ simulators
def simulate(asset_id: str, mode: str, amount: float, years: float | None = None,
             start: date | None = None, end: date | None = None, step_up_pct: float = 0.0) -> dict[str, Any]:
    s = close_series(asset_id)
    end_ts = pd.Timestamp(end) if end else s.index[-1]
    if start is None:
        start_ts = end_ts - pd.DateOffset(days=int(round((years or 5) * 365.25)))
    else:
        start_ts = pd.Timestamp(start)
    if start_ts < s.index[0]:
        start_ts = s.index[0]
    if mode == "sip":
        res = simulate_sip(s, amount, start_ts, end_ts, step_up_pct)
    else:
        res = simulate_lumpsum(s, amount, start_ts, end_ts)
    fd_rates, cpi = macro_rates()
    fd = benchmark_path(res["path"], fd_rates) if fd_rates else []
    infl = benchmark_path(res["path"], cpi) if cpi else []
    path = [{"date": p["date"], "invested": p["invested"], "value": p["value"],
             "fd_value": fd[i]["value"] if fd else None, "inflation_value": infl[i]["value"] if infl else None}
            for i, p in enumerate(res["path"])]
    res["path"] = path
    res["fd_final"] = fd[-1]["value"] if fd else None
    res["inflation_final"] = infl[-1]["value"] if infl else None
    res["asset_id"] = asset_id
    res["years"] = round((pd.Timestamp(res["end"]) - pd.Timestamp(res["start"])).days / 365.25, 2)
    return m.to_jsonable(res)


@cached("compare", ttl=300)
def compare(ids: list[str]) -> dict[str, Any]:
    out = []
    series = {}
    for aid in ids[:4]:
        a = get_asset(aid)
        snap = get_metrics(aid)
        out.append({"asset": a, "metrics": snap})
        series[aid] = close_series(aid)
    common_start = max(s.index[0] for s in series.values())
    growth = {}
    for aid, s in series.items():
        w = s[s.index >= common_start]
        w = w.resample("W-FRI").last().dropna()
        growth[aid] = [{"date": d.strftime("%Y-%m-%d"), "value": round(float(v / w.iloc[0] * 100), 3)} for d, v in w.items()]
    return {"assets": out, "growth_of_100": growth, "common_start": common_start.strftime("%Y-%m-%d")}
