# Deploying WealthLens (free tiers)

| Piece | Service | Notes |
|---|---|---|
| Database | **Supabase** or **Neon** (Postgres) | Copy the connection string → `DATABASE_URL=postgresql+psycopg://...` (add `?sslmode=require`) |
| Cache | **Upstash Redis** | `REDIS_URL=rediss://default:...@...upstash.io:6379` |
| Backend | **Railway** or **Render** | Deploy from the repo root using the `Dockerfile`. Set env vars from `.env.example`. Health check path: `/health` |
| Frontend | **Vercel** | Root directory `frontend`. Env: `NEXT_PUBLIC_API_URL=https://your-api.up.railway.app` |
| Errors | **Sentry** | `SENTRY_DSN=...` on the backend |
| Uptime | **UptimeRobot** | Monitor `https://your-api/health` every 5 min (also keeps free-tier dynos awake) |

## Steps
1. Create the database. From your laptop, point `DATABASE_URL` at it and run `python -m pipeline seed` once, which loads 20 years of history from your machine. Then run `powerbi/views.sql` if you use Power BI.
2. Deploy the backend with these env vars: `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS=https://your-app.vercel.app`, `SENTRY_DSN`, `ENVIRONMENT=production`, and `WEB_CONCURRENCY=1` (the scheduler runs in-process; for more instances, see ARCHITECTURE.md › Scaling).
3. Deploy the frontend to Vercel with `NEXT_PUBLIC_API_URL`.
4. Add the UptimeRobot monitor.
5. **Measure for your resume:** run the load test against the deployed API from another machine:
   ```bash
   python -m tests.load.bench --host https://your-api.up.railway.app --users 500 --seconds 60
   ```
   (or `locust -f tests/load/locustfile.py --host ... --headless -u 500 -r 50 -t 1m` on macOS/Linux). The raised rate limit for this test is `RATE_LIMIT=100000/minute`; set it back afterwards.

> Free backend hosting sleeps when idle, so the first request after a pause is slow. Before interviews, use the uptime ping or a $5/month plan.

## CI/CD
`.github/workflows/ci.yml` runs on every push: ruff → pytest → offline AI eval → eslint, tsc, next build → Docker builds. Connect Vercel and Railway to the GitHub repo for automatic deploys on `main`.
