# WealthLens: Power BI dashboard

The web app is for end users. The Power BI report is the **analyst view**: a star schema, DAX time intelligence, drill-through and what-if parameters. It uses the same data the pipeline loads.

> A `.pbix` file is a binary that only Power BI Desktop can create. This folder has everything you need to build it in about 2 hours, plus a page-by-page spec. Save your file as `powerbi/WealthLens.pbix`, then add screenshots to `powerbi/screenshots/`.

## 1. Get the data in

**Option A: CSV (simplest, works with the default SQLite setup)**
```bash
python -m pipeline export-csv      # writes powerbi/data/dim_asset.csv, dim_date.csv, fact_prices.csv, dim_macro.csv
```
Power BI Desktop: **Get Data → Text/CSV** and load all four files.

**Option B: live PostgreSQL (docker-compose, Supabase or Neon)**
1. Run [`views.sql`](views.sql) against the database.
2. **Get Data → PostgreSQL**, enter the server and database, choose **Import**, then select the `v_*` views.
3. Publish to Power BI Service and set up **scheduled refresh** (Supabase/Neon need the on-premises gateway or a cloud connection).

## 2. Model (star schema)

```
            dim_date (date, year, quarter, month, month_name, weekday)
                │ 1
                │
                ▼ *
dim_asset ─1──*► fact_prices (asset_id, date, close, daily_return, running_peak, drawdown)
                │
dim_macro (year, cpi_inflation, fd_rate)   ← related via dim_date[year] (single direction)
```
- Mark `dim_date` as the **Date table** (Table tools → Mark as date table).
- Hide the foreign keys in `fact_prices`.
- Paste the measures from [`measures.dax`](measures.dax) into a `_Measures` table.
- Import the theme: View → Themes → Browse → [`wealthlens-theme.json`](wealthlens-theme.json).

## 3. Pages

| # | Page | Visuals | Advanced features |
|---|------|---------|-------------------|
| 1 | **Overview** | KPI cards (Return 1Y, 5Y CAGR, Volatility, Max Drawdown), small multiples of price by asset, bar chart of 5Y CAGR, **risk vs return scatter** (x = Volatility, y = CAGR, size = years of data) | Field parameter to switch the scatter Y-axis between CAGR / Real CAGR / Return 1Y |
| 2 | **Asset deep dive** (drill-through on `dim_asset[name]`) | Line chart of close with 50/200-day moving averages, **calendar heatmap** (matrix: rows = month, columns = day, conditional formatting on daily_return), drawdown area chart | Drill-through, custom **tooltip page** showing the mini drawdown chart |
| 3 | **What-if calculator** | Slicers for `Monthly SIP` and `Invest Years` what-if parameters; cards for SIP Invested / SIP Future Value / Lumpsum Future Value; bar compare vs FD | What-if parameters |
| 4 | **Dip history** | Table of drawdown episodes (from `v_fact_drawdown`, filtered with drawdown ≤ -10%), histogram of forward returns | Bookmarks to toggle the 10% / 20% thresholds |

Also add:
- **Calculation group** (Tabular Editor) called *Time Calc* with items `Current`, `YTD`, `1Y`, `5Y CAGR`, so a single measure can switch between time periods.
- **Mobile layout** (View → Mobile layout) for page 1.
- A disclaimer text box on every page: *Educational. Not investment advice. Not SEBI-registered. Data is delayed and indicative.*

## 4. Showcase
- Record a 60–90 second walkthrough (drill-through, the what-if slider, a bookmark toggle).
- Add 3–4 screenshots to `powerbi/screenshots/` and link them from the main README.
