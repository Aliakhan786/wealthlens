# Architecture

## Request path (what happens when someone opens an asset page)

1. The **Next.js** client page fires about 7 parallel React Query requests (`/assets/{id}`, `/prices`, `/metrics`, `/drawdown`, `/calendar`, `/dip-history`, `/news`). Skeleton loaders show until each one resolves.
2. **FastAPI** looks up the serialised JSON in the cache (`api:resp:<route>:<params>`):
   - **hit**: the bytes are returned directly, with no pandas work and no JSON encoding.
   - **miss**: `services.py` reads the pre-computed `metrics_snapshot` row, or the price series (itself memoised per process for 2 min), computes the response, serialises it once and stores it with a TTL (5–10 min).
3. The pipeline **invalidates** `api:*` keys after each refresh, so users never see stale analytics for longer than one refresh cycle.
4. Live prices come over one shared **SSE** connection per browser tab. The server pushes a frame only when the snapshot changes and sends a heartbeat every 15 s. If SSE fails, the client falls back to polling `/live`.

## Data pipeline (ETL)

| Step | Code | Notes |
|---|---|---|
| Extract | `pipeline/fetchers.py` | yfinance (auto-adjusted), mfapi.in, derived gold/silver (USD futures × USD/INR ÷ 31.1035 g/oz). If a source fails, the pipeline falls back to deterministic sample data flagged `is_synthetic`. |
| Clean | `pipeline/cleaning.py` | Dedupe, drop non-positive values, remove one-day spikes that fully reverse, **back-adjust missed splits** (a persistent ≥3× one-day jump), and fill OHLC from close for NAVs. |
| Load | `pipeline/load.py` | Portable upsert (delete the overlapping window, then bulk insert). Fetches run in parallel; writes are serialised (SQLite has a single writer). A refresh never overwrites real history with sample data. |
| Precompute | `analytics/snapshot.py` | Trailing returns, CAGR, volatility and risk label, max drawdown and recovery, best/worst day, streaks, yearly returns, rolling 1/3/5Y, real return vs CPI, excess over FD, and dip summaries at 10% and 20%. |
| Schedule | `pipeline/scheduler.py` | Live quotes every 2 min, EOD refresh at 18:30 IST, NAV refresh at 23:30 IST, news every 30 min. Runs in-process (single instance) or standalone (`python -m pipeline.scheduler`). |

## AI layer

```
user question ──► classify_input (EN/HI regex) ──► tag: ok | advice | prediction
                         │
          ┌──────────────┴──────────────┐
   API key present                   no key
          │                              │
  Claude + 5 tools (manual loop,      rule-based intent parser
  ≤6 steps, effort=low, cached        calling the *same* tools
  system prompt, refusal fallbacks)
          └──────────────┬──────────────┘
                         ▼
          sanitize_output: drop advice/forecast sentences, add disclaimer
                         ▼
                 cache (6 h) ──► response + tool trace + news sources
```

- **Grounding:** the model gets numbers only through tool results or a `<data>` block, and the prompt forbids figures from anywhere else. The eval measures this: every percentage in an answer must match a tool output within ±0.15 pp.
- **Retrieval:** news is tagged to assets by keyword and embedded with a 512-dim signed hashing vectoriser. Ranking is `0.7·cosine + 0.3·recency + asset-tag bonus`.
- **Cost control:** answers are cached by question (6 h), explanations by `(asset, language, data date)`, the system prompt uses prompt caching, and `effort: low` is used for short educational answers.

## Scaling notes
- The API is **stateless**: cache and rate-limit storage move to Redis when `REDIS_URL` is set, so you can run N instances behind a load balancer.
- Run the scheduler as **one** separate process (`python -m pipeline.scheduler`) and set `ENABLE_SCHEDULER=false` on the API instances when you scale out.
- Postgres uses SQLAlchemy connection pooling (`pool_size=10, max_overflow=20, pre_ping`).
