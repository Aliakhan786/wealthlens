-- Star schema views for Power BI (PostgreSQL). Run once against the WealthLens database.
-- Power BI: Get Data → PostgreSQL → server/db → select the v_* views (Import mode).

CREATE OR REPLACE VIEW v_dim_asset AS
SELECT id AS asset_id, name, asset_class, unit, risk_category, is_synthetic, first_date, last_date
FROM assets;

CREATE OR REPLACE VIEW v_fact_prices AS
SELECT p.asset_id,
       p.date,
       p.close,
       p.close / LAG(p.close) OVER w - 1                       AS daily_return,
       MAX(p.close) OVER (PARTITION BY p.asset_id ORDER BY p.date
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_peak
FROM prices_daily p
WINDOW w AS (PARTITION BY p.asset_id ORDER BY p.date);

CREATE OR REPLACE VIEW v_fact_drawdown AS
SELECT asset_id, date, close, running_peak, close / running_peak - 1 AS drawdown
FROM v_fact_prices;

CREATE OR REPLACE VIEW v_dim_macro AS
SELECT year, cpi_inflation / 100.0 AS cpi_inflation, fd_rate / 100.0 AS fd_rate FROM macro;

-- Pre-computed metrics flattened for KPI cards
CREATE OR REPLACE VIEW v_metrics AS
SELECT asset_id,
       (payload ->> 'cagr_since_start')::float                 AS cagr_since_start,
       (payload ->> 'volatility')::float                       AS volatility,
       payload ->> 'risk_label'                                 AS risk_label,
       (payload -> 'max_drawdown' ->> 'depth')::float          AS max_drawdown,
       (payload -> 'trailing' -> '1Y' ->> 'absolute')::float   AS return_1y,
       (payload -> 'trailing' -> '5Y' ->> 'cagr')::float       AS cagr_5y,
       (payload -> 'trailing' -> '10Y' ->> 'cagr')::float      AS cagr_10y,
       (payload -> 'benchmarks' ->> 'real_cagr')::float        AS real_cagr,
       computed_at
FROM metrics_snapshot;
