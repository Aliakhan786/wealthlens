<div align="center">

# 👁️ WealthLens

### Make sense of your savings

**20 years of history for gold, silver, Nifty, Sensex and popular Indian mutual funds: returns, risk, crashes and recoveries, explained in plain English and Hindi by an AI that is grounded in real data and never gives buy/sell tips.**

`Python` · `pandas` · `FastAPI` · `PostgreSQL / SQLite` · `Redis` · `Claude (tool use + RAG)` · `Next.js 14` · `TypeScript` · `Tailwind` · `Framer Motion` · `TradingView Lightweight Charts` · `Power BI` · `Docker` · `GitHub Actions`

</div>

---

> ⚠️ **Educational tool. Not investment advice. Not SEBI-registered.** Market data is delayed and indicative.

## ✨ What it does

| Feature | What you see | Under the hood |
|---|---|---|
| **Explore** | 18 assets with live (delayed) prices that flash green/red, sparklines and risk labels | One shared **Server-Sent Events** stream; risk is computed from annualised volatility |
| **Asset deep dive** | TradingView-style chart (line/candles, 50/200-DMA), 12 key stats, rolling returns, yearly bars, drawdown chart, **daily P&L calendar heatmap**, monthly returns grid, news | All metrics **pre-computed** by the pipeline into `metrics_snapshot`, served as cached JSON |
| **What-if simulator** | Sliders for SIP / lump sum / step-up, with a growth chart compared against **FD and inflation** | Back-tested on real prices, with **XIRR** solved by bisection |
| ⭐ **History says** | "When gold fell 10%+ from its peak, what happened 1/3/5 years later?" Win-rate rings and an animated timeline | Drawdown-episode detector that re-arms only after a new all-time high, so one crash counts once |
| **Risk quiz** | 6-question card flow ending in an animated pie of an *educational* mix | Safety caps: no emergency fund or a horizon under 1 year means it never shows "Aggressive" |
| **Compare** | Growth of ₹100 for 2–4 assets plus a metrics table | Aligned on the first common date |
| **Explain this to me** (EN / हिंदी) | A plain-language summary of the asset page | Claude receives **only our computed numbers** and is told to use nothing else |
| **Ask WealthLens** | A chat that answers "What if I put ₹1 lakh in Nifty for 5 years?" with a "Show work" panel | **Agentic tool use**: Claude calls `simulate`, `get_metrics`, `dip_history` and `search_news` (RAG) on our own analytics |
| **Guardrails** | Never says buy/sell, never predicts, always shows a disclaimer | Input classifier (EN + HI), output sanitiser and server-side refusal fallbacks |
| **Works offline** | No API key or internet? Everything still runs | Deterministic fallbacks: an offline agent, template explanations and labelled sample data |

## 🏗️ Architecture

```
 ┌──────────── DATA SOURCES (free) ────────────┐
 │ yfinance: GC=F, SI=F, ^NSEI, ^BSESN, …       │
 │ mfapi.in: AMFI mutual-fund NAVs             │
 │ RSS: ET, Moneycontrol, Livemint             │
 │ CSV: CPI inflation, FD rates                │
 └──────────────────────┬──────────────────────┘
                        ▼
  ⏱️ pipeline/ (APScheduler)   extract → clean (bad ticks, missed splits) → load → precompute
     live quotes every 2 min · EOD refresh 18:30 IST · NAV refresh 23:30 IST · news every 30 min
                        ▼
  🗄️ PostgreSQL (or SQLite)  assets · prices_daily · prices_live · metrics_snapshot · macro · news(+embeddings)
           │                                   └──► 📊 Power BI (star-schema views, DAX)
           ▼
  ⚡ backend/ FastAPI   cached JSON responses (Redis/in-memory) · SSE live stream · slowapi rate limits
           │            Pydantic validation · GZip · Sentry · /health
           ▼
  🤖 ai/  explainer · tool-using agent · news retrieval · guardrails · eval harness
           ▼
  🎨 frontend/ Next.js 14 · React Query · Framer Motion · Lightweight Charts · Recharts · dark/light
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · design trade-offs: [docs/DECISIONS.md](docs/DECISIONS.md)

## 🚀 Run it on your laptop

**Prerequisites:** Python 3.12+, Node.js 20+.

### Windows (one command each)
```bash
setup.cmd
```
```bash
start.cmd
```
`setup.cmd` creates the virtual environment, installs dependencies, downloads 20 years of data (about 30 s) and runs the tests. `start.cmd` opens the API and the web app in two windows and launches http://localhost:3000.

### macOS / Linux
```bash
bash scripts/setup.sh
```
```bash
bash scripts/start.sh
```

### Manual
```bash
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pipeline seed                             # or: python -m pipeline seed --offline
uvicorn backend.main:app --port 8000                # API docs: http://127.0.0.1:8000/docs
cd frontend && npm install && npm run dev           # http://localhost:3000
```

### Full production-like stack (Postgres + pgvector + Redis)
```bash
docker compose up --build
```

### Turn on the AI
Add `ANTHROPIC_API_KEY=...` to `.env` and restart the API. Without it, the AI features use the offline agent and template explanations.

## ✅ Quality, measured

| Check | Result |
|---|---|
| Unit + API tests (`pytest`) | **34 passing**: analytics maths (CAGR, XIRR, drawdown, dips, split adjustment), every endpoint, guardrails |
| AI eval, 32 questions incl. Hindi (`python -m ai.eval.run_eval`) | Guardrail compliance **100%** · advice/prediction requests caught **100%** · tool routing **100%** · numeric faithfulness **93%** (offline agent; re-run with a key to score the LLM) |
| Lint / types / build | `ruff` clean · `eslint` clean · `tsc` clean · `next build` ✓ |
| Load test (`python -m tests.load.bench`) | Dev laptop (6-core, 7 GB, client and server on one machine, dev servers running): 200 concurrent users, **0.09% errors**, p50 0.7 s. Re-run on deployed infrastructure for a production figure (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)). |

Data-quality checks found and fixed real issues, for example GOLDBEES' 1:100 unit split, which Yahoo leaves unadjusted and which showed up as a fake −99% crash.

## 📁 Project structure

```
wealthlens/
├── core/          config (pydantic-settings) + SQLAlchemy models
├── pipeline/      fetchers, cleaning, loader, live quotes, news, scheduler, CSV export (CLI: python -m pipeline)
├── analytics/     metrics, simulators (SIP/lump sum/XIRR), dip analyzer, snapshot builder
├── backend/       FastAPI app, routes, services, cache, rate limiter, quiz
├── ai/            prompts, LLM client, explainer, agent + tools, retrieval, guardrails, eval/
├── frontend/      Next.js app (src/app/*), components, e2e tests (Playwright)
├── powerbi/       star-schema SQL views, DAX measures, theme, build guide
├── tests/         pytest suites + load tests (Locust and an asyncio bench)
├── docs/          architecture, decisions, deployment, interview prep
└── .github/       CI: lint, tests, AI eval, frontend build, Docker builds
```

## 🔌 API

Interactive docs at `/docs` (Swagger) once the API is running.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/assets?risk=&asset_class=` | All assets with summary cards |
| GET | `/assets/{id}/prices?range=1M…MAX` | OHLC + 50/200-DMA (weekly candles for long ranges) |
| GET | `/assets/{id}/metrics` | Returns, risk, drawdown, rolling, benchmarks |
| GET | `/assets/{id}/calendar?year=` | Daily P&L heatmap + monthly grid |
| GET | `/assets/{id}/drawdown` | Drawdown series + worst episodes |
| GET | `/assets/{id}/dip-history?threshold=10` | Historical dip outcomes |
| GET | `/compare?ids=a,b,c` | Side-by-side comparison |
| POST | `/simulate/sip`, `/simulate/lumpsum` | Back-tested simulators |
| GET/POST | `/quiz/questions`, `/quiz/risk-profile` | Risk quiz |
| GET | `/live`, `/stream/live` | Latest quotes / SSE stream |
| POST | `/ai/explain`, `/ai/ask` | AI layer (rate-limited separately) |
| GET | `/news/{id}` | Retrieved news for an asset |
| GET | `/health` | DB, cache, LLM status and data freshness |

## 🛡️ Responsible by design
- No buy/sell signals, no price predictions, no handling of money, no login and no personal financial data.
- A disclaimer on every page and in every AI answer. Data is labelled delayed/indicative, with sources credited.
- Secrets live in environment variables only (`.env` is git-ignored). CORS is allow-listed, every input is validated, and the AI endpoints have a stricter rate limit.

## 🗺️ Roadmap
- [ ] Deploy (Vercel + Railway + Supabase + Upstash) and add the live URL here
- [ ] Build the Power BI report from [`powerbi/`](powerbi/README.md) and add screenshots
- [ ] Swap hashing embeddings for neural embeddings in pgvector
- [ ] Record a 2-minute demo GIF for this README

## 📜 Data credits
Yahoo Finance (via [yfinance](https://github.com/ranaroussi/yfinance)), [mfapi.in](https://www.mfapi.in/) (AMFI NAVs), Economic Times, Moneycontrol, Livemint (RSS headlines, linked to the original articles). For educational use.
