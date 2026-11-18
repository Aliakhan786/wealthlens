"""Load step + orchestration: fetch → clean → upsert → precompute metrics."""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select

from analytics.snapshot import compute_snapshot
from core.config import get_settings
from core.db import Asset, Macro, MetricsSnapshot, PriceDaily, init_db, session_scope
from pipeline.assets import ASSETS, AssetDef
from pipeline.cleaning import clean_prices
from pipeline.fetchers import fetch_asset_history

log = logging.getLogger("wealthlens.load")
MACRO_CSV = Path(__file__).parent / "data" / "macro_india.csv"
WRITE_LOCK = threading.Lock()


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def load_macro() -> None:
    df = pd.read_csv(MACRO_CSV)
    with session_scope() as s:
        s.execute(delete(Macro))
        s.add_all(Macro(year=int(r.year), cpi_inflation=float(r.cpi_inflation), fd_rate=float(r.fd_rate))
                  for r in df.itertuples())
    log.info("Loaded %d macro rows", len(df))


def macro_frame() -> pd.DataFrame:
    with session_scope() as s:
        rows = s.execute(select(Macro.year, Macro.cpi_inflation, Macro.fd_rate)).all()
    return pd.DataFrame(rows, columns=["year", "cpi_inflation", "fd_rate"])


def upsert_prices(asset: AssetDef, df: pd.DataFrame, is_synthetic: bool, replace_all: bool) -> int:
    """Portable upsert (works on SQLite and Postgres): delete the overlapping window, bulk insert."""
    if df.empty:
        return 0
    first = df.index[0].date()
    with WRITE_LOCK, session_scope() as s:  # fetches run in parallel; writes are serialised (SQLite has one writer)
        q = delete(PriceDaily).where(PriceDaily.asset_id == asset.id)
        if not replace_all:
            q = q.where(PriceDaily.date >= first)
        s.execute(q)
        s.bulk_insert_mappings(PriceDaily, [
            {"asset_id": asset.id, "date": d.date(), "open": _f(r.open), "high": _f(r.high),
             "low": _f(r.low), "close": float(r.close), "volume": _f(r.volume)}
            for d, r in df.iterrows()
        ])
        row = s.get(Asset, asset.id) or Asset(id=asset.id)
        row.name, row.asset_class, row.symbol, row.source = asset.name, asset.asset_class, asset.symbol, asset.source
        row.unit, row.description = asset.unit, asset.description
        row.is_synthetic = is_synthetic if replace_all else (row.is_synthetic and is_synthetic)
        row.updated_at = utcnow()
        s.merge(row)
    return len(df)


def _f(v) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def price_series(asset_id: str) -> pd.Series:
    with session_scope() as s:
        rows = s.execute(select(PriceDaily.date, PriceDaily.close)
                         .where(PriceDaily.asset_id == asset_id).order_by(PriceDaily.date)).all()
    if not rows:
        return pd.Series(dtype="float64")
    return pd.Series([r[1] for r in rows], index=pd.to_datetime([r[0] for r in rows]))


def refresh_snapshot(asset_id: str, macro: pd.DataFrame | None = None) -> None:
    series = price_series(asset_id)
    if len(series) < 30:
        return
    snap = compute_snapshot(series, macro if macro is not None else macro_frame())
    with session_scope() as s:
        s.merge(MetricsSnapshot(asset_id=asset_id, computed_at=utcnow(), payload=snap))
        a = s.get(Asset, asset_id)
        if a:
            a.risk_category = snap.get("risk_label")
            a.first_date, a.last_date = series.index[0].date(), series.index[-1].date()


def _process(asset: AssetDef, years: float, replace_all: bool, offline: bool) -> tuple[str, int, bool]:
    raw, synthetic = fetch_asset_history(asset, years, offline=offline)
    if not replace_all and synthetic:
        return asset.id, 0, True  # never overwrite real history with sample data during a refresh
    clean = clean_prices(raw)
    n = upsert_prices(asset, clean, synthetic, replace_all)
    return asset.id, n, synthetic


def run_full_load(offline: bool | None = None) -> None:
    """Initial backfill: ~20 years of daily history for every asset."""
    settings = get_settings()
    offline = settings.offline_mode if offline is None else offline
    init_db()
    load_macro()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda a: _process(a, settings.history_years, True, offline), ASSETS))
    for aid, n, synth in results:
        log.info("%-20s %6d rows %s", aid, n, "(sample data)" if synth else "")
    recompute_all_snapshots()


def run_daily_refresh() -> None:
    """Incremental: re-pull the last ~45 days (catches late NAVs and revisions) and recompute metrics."""
    settings = get_settings()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda a: _process(a, 45 / 365, False, settings.offline_mode), ASSETS))
    recompute_all_snapshots()
    log.info("Daily refresh complete")


def recompute_all_snapshots() -> None:
    macro = macro_frame()
    for a in ASSETS:
        try:
            refresh_snapshot(a.id, macro)
        except Exception:  # one bad series shouldn't block the rest
            log.exception("Snapshot failed for %s", a.id)
    try:
        from backend.cache import cache

        cache.clear_prefix("api:")  # invalidate API responses that depend on prices
    except Exception:
        pass


def database_is_empty() -> bool:
    init_db()
    with session_scope() as s:
        return s.execute(select(PriceDaily.asset_id).limit(1)).first() is None


def last_refresh_age() -> timedelta | None:
    with session_scope() as s:
        ts = s.execute(select(MetricsSnapshot.computed_at).order_by(MetricsSnapshot.computed_at.desc())).scalar()
    return (utcnow() - ts) if ts else None
