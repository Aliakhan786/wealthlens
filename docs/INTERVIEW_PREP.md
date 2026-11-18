# Resume bullets & interview prep

## Resume bullets (choose 3–4, then update the numbers once deployed)

- Built **WealthLens**, a full-stack fintech analytics platform (FastAPI, PostgreSQL, Next.js) that turns 20 years of market data for 18 Indian assets (≈70K daily prices) into plain-language insights on returns, risk and recovery.
- Designed a Python **ETL pipeline** (yfinance, AMFI NAVs, RSS) with APScheduler. It detects and back-adjusts unadjusted stock splits and bad ticks, and pre-computes metrics so API reads need no on-request computation.
- Implemented a tested **analytics engine** (CAGR, XIRR, rolling returns, max drawdown and recovery, SIP vs lump-sum back-tests, and a historical dip analyzer with 1/3/5-year win rates), covered by 34 pytest tests.
- Built an **agentic AI assistant** (Claude tool use + news retrieval) that answers questions by calling the platform's own analytics. It scores **100% on guardrail compliance** and **93% on numeric faithfulness** across a 32-question English/Hindi eval suite that runs in CI.
- Shipped a **Next.js + Framer Motion** frontend with TradingView charts, live price streaming over **Server-Sent Events**, a calendar heatmap and what-if simulators, backed by Redis response caching, rate limiting, Docker and GitHub Actions CI.
- *(after deploying)* Load-tested with Locust: **N concurrent users at p95 X ms** on a $5 instance.

## Questions you'll get, and how to answer them

**"Why did you pre-compute metrics?"** Reads vastly outnumber writes: prices change a few times a day, while every visitor needs the same numbers. Computing once per refresh and caching the serialised response turns a pandas job into a key lookup. I also profiled and found that JSON re-encoding of large payloads was the next bottleneck, so I cache bytes rather than objects.

**"How does your caching work? What about invalidation?"** There are two layers. A per-process series memo (2 min) avoids re-reading prices from the DB, and a shared Redis cache of serialised responses uses route-specific TTLs (30 s for lists, 5–10 min for analytics, 6 h for AI answers). The pipeline clears the `api:*` keys after each refresh, so staleness is bounded by the refresh cycle.

**"How did you stop the AI from giving financial advice?"** There are three layers. (1) The prompt forbids buy/sell, rankings and forecasts and requires figures to come only from tool data. (2) An input classifier (English and Hindi) detects advice and prediction requests and steers the model to reframe with historical facts. (3) An output sanitiser removes any sentence matching advice or forecast patterns and always appends the disclaimer. It's measured by an eval in CI, so a prompt change that weakens it fails the build.

**"How do you know the AI isn't making numbers up?"** The model never computes; it calls my tested Python functions. The eval extracts every percentage from each answer and checks it against the tool outputs (±0.15 pp). It's 93% today, and the misses are rounding and derived figures I can show.

**"Why SSE and not WebSockets?"** One-way data, plain HTTP, built-in reconnection, and it works through proxies. There's one shared stream per browser tab, and the server only pushes when data changes.

**"What was the hardest bug?"** GOLDBEES showed a −99% crash. Yahoo hadn't adjusted its 1:100 unit split. I added a cleaning rule that treats a persistent ≥3× one-day jump as a corporate action and back-adjusts history, with a unit test. Real data is messy, and validating it is part of the job.

**"How would you scale to 100× traffic?"** The API is already stateless with Redis-backed cache and rate limits, so I'd run more instances behind a load balancer, move the scheduler to a single worker process, put a CDN in front of the cacheable GET routes (they already send `Cache-Control`), and use read replicas for Postgres.

**"Why these risk thresholds?"** I calibrated them on the actual universe. Textbook cut-offs labelled the Nifty 50 "High risk", which would scare a first-time investor away from the most diversified option. Context matters more than convention.

## LinkedIn post outline
1. **Hook:** "Most people in India choose between gold, FDs and mutual funds based on a relative's advice. I built a tool that shows what 20 years of data actually say."
2. **Problem → solution:** 3 bullets (history in plain language, what-if simulator, "history says" dip analyzer).
3. **Tech:** pipeline → FastAPI → Next.js, plus an AI that calls real analytics and never gives tips.
4. **Numbers:** eval scores and the load test.
5. **Demo GIF + live link + GitHub.**
