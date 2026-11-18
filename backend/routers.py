"""All HTTP routes. Business logic lives in services / analytics / ai — routes stay thin."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select, text

from ai import agent, explainer
from ai.llm import llm_available
from ai.rag import search_news
from backend import quiz, services
from backend.cache import cache
from backend.limiter import limiter
from backend.schemas import AskRequest, ExplainRequest, QuizRequest, SimulateRequest
from core.config import get_settings
from core.db import PriceLive, engine, session_scope

router = APIRouter()
settings = get_settings()


def _404(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except services.NotFound as e:
        raise HTTPException(404, f"Asset '{e}' not found") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


def _json(key: str, ttl: int, fn, *a, **kw) -> Response:
    """Serve pre-serialised JSON straight from cache.

    Market data is identical for every visitor, so the expensive parts (pandas work *and* JSON encoding of
    large chart payloads) happen once per TTL per instance instead of once per request.
    """
    key = f"api:resp:{key}"
    raw = cache.get_raw(key)
    if raw is None:
        raw = json.dumps(_404(fn, *a, **kw), default=str, separators=(",", ":"))
        cache.set_raw(key, raw, ttl)
    return Response(raw, media_type="application/json")


# ------------------------------------------------------------------ health
@router.get("/health", tags=["ops"])
def health():
    db_ok = True
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    from pipeline.load import last_refresh_age

    age = last_refresh_age() if db_ok else None
    return {"status": "ok" if db_ok else "degraded", "db": db_ok, "cache": cache.backend,
            "cache_hits": cache.hits, "cache_misses": cache.misses, "llm": llm_available(),
            "data_age_minutes": round(age.total_seconds() / 60, 1) if age else None,
            "time": datetime.now(UTC).isoformat()}


# ------------------------------------------------------------------ assets
@router.get("/assets", tags=["assets"])
def assets(risk: str | None = Query(None, pattern="^(Low|Medium|High)$"), asset_class: str | None = None):
    def build():
        rows = services.list_assets()
        if risk:
            rows = [r for r in rows if r["risk"] == risk]
        if asset_class:
            rows = [r for r in rows if r["asset_class"] == asset_class]
        return rows

    return _json(f"assets:{risk}:{asset_class}", 30, build)


@router.get("/assets/{asset_id}", tags=["assets"])
def asset(asset_id: str):
    return _json(f"asset:{asset_id}", 30, services.get_asset, asset_id)


@router.get("/assets/{asset_id}/prices", tags=["assets"])
def prices(asset_id: str, range: str = Query("1Y", pattern="^(1M|6M|1Y|3Y|5Y|10Y|MAX)$")):
    return _json(f"prices:{asset_id}:{range}", 300, services.get_prices, asset_id, range)


@router.get("/assets/{asset_id}/metrics", tags=["assets"])
def asset_metrics(asset_id: str):
    return _json(f"metrics:{asset_id}", 300, services.get_metrics, asset_id)


@router.get("/assets/{asset_id}/calendar", tags=["assets"])
def calendar(asset_id: str, year: int | None = Query(None, ge=1990, le=2100)):
    return _json(f"calendar:{asset_id}:{year}", 600, services.get_calendar, asset_id, year)


@router.get("/assets/{asset_id}/drawdown", tags=["assets"])
def drawdown(asset_id: str):
    return _json(f"drawdown:{asset_id}", 600, services.get_drawdown, asset_id)


@router.get("/assets/{asset_id}/dip-history", tags=["assets"])
def dip_history(asset_id: str, threshold: float = Query(10, ge=3, le=60, description="% fall from peak")):
    return _json(f"dips:{asset_id}:{threshold}", 600, services.get_dip_history, asset_id, threshold / 100)


@router.get("/compare", tags=["assets"])
def compare(ids: str = Query(..., description="comma-separated asset ids, 2–4")):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not 2 <= len(id_list) <= 4:
        raise HTTPException(422, "Pass 2 to 4 asset ids")
    return _json(f"compare:{','.join(id_list)}", 300, services.compare, id_list)


# ------------------------------------------------------------------ simulators
@router.post("/simulate/sip", tags=["simulate"])
def simulate_sip(body: SimulateRequest):
    return _json(f"sip:{body.model_dump_json()}", 600, services.simulate, body.asset_id, "sip", body.amount, body.years,
                 body.start, body.end, body.step_up_pct)


@router.post("/simulate/lumpsum", tags=["simulate"])
def simulate_lumpsum(body: SimulateRequest):
    return _json(f"lumpsum:{body.model_dump_json()}", 600, services.simulate, body.asset_id, "lumpsum", body.amount,
                 body.years, body.start, body.end)


# ------------------------------------------------------------------ quiz
@router.get("/quiz/questions", tags=["quiz"])
def quiz_questions():
    return quiz.QUESTIONS


@router.post("/quiz/risk-profile", tags=["quiz"])
def quiz_profile(body: QuizRequest):
    try:
        return quiz.score_quiz(body.answers)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None


# ------------------------------------------------------------------ live stream (SSE)
def _live_snapshot() -> list[dict]:
    hit = cache.get("api:live")
    if hit is not None:
        return hit
    with session_scope() as s:
        rows = s.execute(select(PriceLive)).scalars().all()
        data = [{"asset_id": r.asset_id, "price": r.price, "change": r.change, "change_pct": r.change_pct,
                 "ts": r.ts.isoformat()} for r in rows]
    cache.set("api:live", data, 15)
    return data


@router.get("/live", tags=["live"])
def live():
    return _live_snapshot()


@router.get("/stream/live", tags=["live"])
async def stream_live(request: Request):
    """Server-Sent Events: pushes the latest (delayed) quotes whenever they change; heartbeat every 15s."""

    async def gen():
        last = None
        yield "retry: 5000\n\n"
        while not await request.is_disconnected():
            data = await run_in_threadpool(_live_snapshot)
            payload = json.dumps(data)
            if payload != last:
                yield f"event: prices\ndata: {payload}\n\n"
                last = payload
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(15)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------ AI
@router.post("/ai/explain", tags=["ai"])
@limiter.limit(settings.ai_rate_limit)
def ai_explain(request: Request, body: ExplainRequest):
    a = _404(services.get_asset, body.asset_id)
    snap = _404(services.get_metrics, body.asset_id)
    return explainer.explain_asset(a, snap, body.lang)


@router.post("/ai/ask", tags=["ai"])
@limiter.limit(settings.ai_rate_limit)
def ai_ask(request: Request, body: AskRequest):
    return agent.ask(body.question, body.lang, [t.model_dump() for t in body.history])


@router.get("/news/{asset_id}", tags=["ai"])
def news(asset_id: str, q: str | None = None, k: int = Query(8, ge=1, le=20)):
    a = _404(services.get_asset, asset_id)
    return search_news(q or f"{a['name']} price market news", asset_id, k=k)
