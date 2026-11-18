"""Pipeline CLI.

    python -m pipeline seed            # full 20-year backfill + metrics + live + news
    python -m pipeline seed --offline  # same, with deterministic sample data (no internet)
    python -m pipeline refresh         # incremental daily refresh
    python -m pipeline live            # one live-price pass
    python -m pipeline news            # one news ingestion pass
    python -m pipeline export-csv      # CSVs for Power BI (powerbi/data/)
"""
from __future__ import annotations

import argparse
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def main() -> None:
    p = argparse.ArgumentParser(prog="pipeline")
    p.add_argument("command", choices=["seed", "refresh", "live", "news", "export-csv"])
    p.add_argument("--offline", action="store_true", help="use deterministic sample data")
    args = p.parse_args()
    t0 = time.time()

    if args.command == "seed":
        from pipeline.live import update_live_prices
        from pipeline.load import run_full_load
        from pipeline.news import ingest_news

        run_full_load(offline=args.offline)
        update_live_prices()
        if not args.offline:
            try:
                ingest_news()
            except Exception as e:
                logging.warning("News ingestion skipped: %s", e)
    elif args.command == "refresh":
        from pipeline.load import run_daily_refresh
        run_daily_refresh()
    elif args.command == "live":
        from pipeline.live import update_live_prices
        update_live_prices()
    elif args.command == "news":
        from pipeline.news import ingest_news
        ingest_news()
    elif args.command == "export-csv":
        from pipeline.export import export_csv
        export_csv()
    logging.info("Done in %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
