# Design decisions (and the trade-offs behind them)

**1. Pre-compute metrics instead of computing them per request.** Market data changes a few times a day, while page views happen constantly. The pipeline writes one `metrics_snapshot` row per asset, so a page view is a key lookup instead of a pandas job. *Trade-off:* metrics lag prices until the next refresh. That's acceptable for long-horizon analytics, and the live price is shown separately.

**2. Cache serialised JSON, not Python objects.** Profiling showed that FastAPI spent most of its time re-encoding large chart payloads (thousands of candles) on every cache hit. Caching the final bytes and returning a raw `Response` removes that work entirely.

**3. SQLite by default, Postgres in production.** A recruiter, or you on a new laptop, can run everything with zero setup. The same SQLAlchemy models run on Supabase or Neon by changing `DATABASE_URL`. *Trade-off:* SQLite allows one writer, so the loader serialises writes behind a lock.

**4. SSE instead of WebSockets for live prices.** The data only flows server → client, SSE works over plain HTTP, reconnects automatically and passes through proxies and CDNs easily. WebSockets would add complexity with no benefit here.

**5. Derived gold price instead of a scraped retail price.** International futures × USD/INR is reproducible, free and has 20+ years of history. *Trade-off:* it excludes import duty, GST and local premiums. The UI and About page say so explicitly.

**6. Detect missed stock splits in the data.** Yahoo leaves some corporate actions unadjusted (GOLDBEES' 1:100 split showed up as a −99% crash). No asset here can genuinely move 3× in a day, so a persistent jump of that size is treated as a split and earlier history is back-adjusted. A test covers it.

**7. Volatility thresholds (Low <10%, Medium <21%, High ≥21%).** These were calibrated on the actual universe: USD/INR comes out Low, gold and the broad indices Medium, and sector indices and silver High. Fixed textbook thresholds put the Nifty 50 in "High", which would mislead a first-time investor.

**8. The AI explains our numbers; it doesn't do the analysis.** Every number comes from deterministic, tested Python. The LLM only turns tool results into language. This keeps answers auditable (the "Show work" panel) and makes faithfulness measurable.

**9. Tool use over plain RAG for questions.** "What if I put ₹1 lakh in Nifty for 5 years?" needs a calculation, not retrieval. The agent calls the same `simulate()` function the simulator page uses, so the chat and the UI can never disagree.

**10. Guardrails in code, not only in the prompt.** Prompts can be ignored, so a regex-based output sanitiser removes advice and forecast sentences and always appends the disclaimer. The eval checks compliance on every run, including in CI.

**11. Hashing embeddings, with pgvector as the upgrade path.** Neural embeddings need either a paid API or a large model download, which hurts the "runs anywhere in 2 minutes" goal. The hashing vectoriser is deterministic and offline. Embeddings are already stored per article, so moving to `vector(512)` plus a neural model only changes `ai/rag.embed()` and the column type.

**12. Offline fallbacks everywhere.** Free APIs rate-limit and go down, and demos happen on bad Wi-Fi. Every external dependency has a labelled fallback, so the app never shows a blank screen.

**13. Windows-specific findings.** Smart App Control blocked SQLAlchemy 2.1's compiled extension and gevent (Locust). SQLAlchemy is pinned to 2.0, which falls back to pure Python, and there's an asyncio load tester that needs no native code. The frontend calls `127.0.0.1` rather than `localhost`, because on Windows `localhost` tries IPv6 first and adds about 200 ms per new connection.
