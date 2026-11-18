"""WealthLens API — run with:  uvicorn backend.main:app --reload"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.limiter import limiter
from backend.routers import router
from core.config import get_settings
from core.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
log = logging.getLogger("wealthlens.api")
settings = get_settings()

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)


def _bootstrap_data() -> None:
    """First run on a fresh machine: seed automatically in the background so the API is usable at once."""
    from pipeline.live import update_live_prices
    from pipeline.load import database_is_empty, run_full_load

    if database_is_empty():
        log.info("Empty database — running initial data load in the background (1–3 min)…")
        run_full_load()
        update_live_prices()
        try:
            from pipeline.news import ingest_news
            ingest_news()
        except Exception as e:
            log.warning("News ingestion skipped: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    threading.Thread(target=_bootstrap_data, daemon=True).start()
    sched = None
    if settings.enable_scheduler:
        from pipeline.scheduler import build_scheduler

        sched = build_scheduler()
        sched.start()
        log.info("Pipeline scheduler started (live every %s min)", settings.live_interval_minutes)
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(
    title="WealthLens API",
    version="1.0.0",
    description="Historical analytics for Indian savings options (gold, silver, indices, mutual funds). "
                "**Educational tool — not investment advice. Not SEBI-registered.** Market data is delayed/indicative.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["GET", "POST"],
                   allow_headers=["*"], allow_credentials=False)


@app.middleware("http")
async def timing_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - t0) * 1000:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith(("/assets", "/compare", "/quiz/questions")) and request.method == "GET":
        response.headers.setdefault("Cache-Control", "public, max-age=30")
    return response


app.include_router(router)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "WealthLens API", "docs": "/docs", "health": "/health",
            "disclaimer": "Educational tool. Not investment advice. Not SEBI-registered."}
