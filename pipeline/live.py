"""Live (delayed ~15 min) quotes → prices_live. Runs every few minutes from the scheduler."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from core.config import get_settings
from core.db import PriceDaily, PriceLive, session_scope
from pipeline.assets import ASSETS, HELPER_SYMBOLS, TROY_OUNCE_GRAMS, AssetDef
from pipeline.fetchers import HTTP, fetch_yahoo_quote
from pipeline.load import utcnow

log = logging.getLogger("wealthlens.live")


def _last_two_closes(asset_id: str) -> tuple[float | None, float | None]:
    with session_scope() as s:
        rows = s.execute(select(PriceDaily.close).where(PriceDaily.asset_id == asset_id)
                         .order_by(PriceDaily.date.desc()).limit(2)).scalars().all()
    return (rows[0] if rows else None, rows[1] if len(rows) > 1 else None)


def quote(asset: AssetDef, fx: tuple[float, float | None] | None) -> tuple[float, float | None]:
    if asset.source == "mfapi":
        d = HTTP.get(f"https://api.mfapi.in/mf/{asset.symbol}", timeout=20).json()["data"]
        return float(d[0]["nav"]), float(d[1]["nav"]) if len(d) > 1 else None
    if asset.source == "derived":
        usd, usd_prev = fetch_yahoo_quote(HELPER_SYMBOLS[f"{asset.id}_usd"])
        rate, rate_prev = fx or fetch_yahoo_quote(HELPER_SYMBOLS["usdinr"])
        grams = 10 if asset.id == "gold" else 1000
        k = grams / TROY_OUNCE_GRAMS
        prev = usd_prev * (rate_prev or rate) * k if usd_prev else None
        return usd * rate * k, prev
    return fetch_yahoo_quote(asset.symbol)


def update_live_prices() -> int:
    settings = get_settings()
    fx = None
    if not settings.offline_mode:
        try:
            fx = fetch_yahoo_quote(HELPER_SYMBOLS["usdinr"])
        except Exception as e:
            log.warning("FX quote failed: %s", e)

    def one(asset: AssetDef):
        try:
            if settings.offline_mode:
                raise RuntimeError("offline")
            price, prev = quote(asset, fx)
        except Exception:
            price, prev = _last_two_closes(asset.id)  # fall back to the last stored close
            if price is None:
                return None
        change = price - prev if prev else None
        return PriceLive(asset_id=asset.id, price=price, prev_close=prev, change=change,
                         change_pct=(change / prev) if prev else None, ts=utcnow())

    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = [r for r in pool.map(one, ASSETS) if r is not None]
    with session_scope() as s:
        for r in rows:
            s.merge(r)
    try:
        from backend.cache import cache

        cache.delete("api:live")
    except Exception:
        pass
    log.info("Live prices updated for %d assets", len(rows))
    return len(rows)
