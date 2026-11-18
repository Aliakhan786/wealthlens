"""APScheduler jobs. Runs inside the API process by default, or standalone: `python -m pipeline.scheduler`."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import get_settings

log = logging.getLogger("wealthlens.scheduler")


def _safe(fn):
    def run():
        try:
            fn()
        except Exception:
            log.exception("Job %s failed", fn.__name__)
    run.__name__ = fn.__name__
    return run


def build_scheduler() -> BackgroundScheduler:
    from pipeline.live import update_live_prices
    from pipeline.load import run_daily_refresh
    from pipeline.news import ingest_news

    settings = get_settings()
    sched = BackgroundScheduler(timezone="Asia/Kolkata", job_defaults={"coalesce": True, "max_instances": 1})
    sched.add_job(_safe(update_live_prices), "interval", minutes=settings.live_interval_minutes, id="live")
    # After NSE close, and again late evening when AMCs have published NAVs
    sched.add_job(_safe(run_daily_refresh), CronTrigger(day_of_week="mon-fri", hour=18, minute=30), id="daily_eod")
    sched.add_job(_safe(run_daily_refresh), CronTrigger(day_of_week="mon-sat", hour=23, minute=30), id="daily_nav")
    sched.add_job(_safe(ingest_news), "interval", minutes=30, id="news")
    return sched


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = build_scheduler()
    s.start()
    log.info("Scheduler running. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        s.shutdown()
