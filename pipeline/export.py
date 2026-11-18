"""Export a Power BI–ready star schema as CSV (for when Power BI can't reach the database directly)."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from core.db import engine

OUT = Path(__file__).resolve().parent.parent / "powerbi" / "data"
log = logging.getLogger("wealthlens.export")


def export_csv() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assets = pd.read_sql("SELECT id AS asset_id, name, asset_class, unit, risk_category, is_synthetic FROM assets", engine)
    prices = pd.read_sql("SELECT asset_id, date, open, high, low, close, volume FROM prices_daily ORDER BY asset_id, date", engine)
    prices["date"] = pd.to_datetime(prices["date"])
    prices["daily_return"] = prices.groupby("asset_id")["close"].pct_change()
    prices["running_peak"] = prices.groupby("asset_id")["close"].cummax()
    prices["drawdown"] = prices["close"] / prices["running_peak"] - 1
    macro = pd.read_sql("SELECT * FROM macro", engine)

    dates = pd.DataFrame({"date": pd.date_range(prices["date"].min(), prices["date"].max(), freq="D")})
    dates["year"], dates["quarter"] = dates.date.dt.year, dates.date.dt.quarter
    dates["month"], dates["month_name"] = dates.date.dt.month, dates.date.dt.strftime("%b")
    dates["weekday"], dates["is_weekend"] = dates.date.dt.day_name(), dates.date.dt.weekday >= 5

    assets.to_csv(OUT / "dim_asset.csv", index=False)
    dates.to_csv(OUT / "dim_date.csv", index=False)
    prices.to_csv(OUT / "fact_prices.csv", index=False)
    macro.to_csv(OUT / "dim_macro.csv", index=False)
    log.info("Exported star schema to %s (%d price rows)", OUT, len(prices))
