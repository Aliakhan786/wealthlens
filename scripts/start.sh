#!/usr/bin/env bash
# macOS / Linux: start API + web app together (Ctrl+C stops both)
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'kill 0' EXIT
.venv/bin/uvicorn backend.main:app --port 8000 &
(cd frontend && npm run dev) &
wait
