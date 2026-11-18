#!/usr/bin/env bash
# macOS / Linux setup. Run from the project root: bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-dev.txt
[ -f .env ] || cp .env.example .env
.venv/bin/python -m pipeline seed || .venv/bin/python -m pipeline seed --offline
(cd frontend && [ -f .env.local ] || cp .env.example .env.local; npm install --no-audit --no-fund)
.venv/bin/python -m pytest -q
echo "Done. Start with: bash scripts/start.sh"
