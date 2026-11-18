"""Test setup: an isolated SQLite DB seeded with deterministic sample data (no network, no API keys)."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_tmp = Path(tempfile.mkdtemp(prefix="wealthlens-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["OFFLINE_MODE"] = "true"
os.environ["REDIS_URL"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["RATE_LIMIT"] = "10000/minute"
os.environ["AI_RATE_LIMIT"] = "10000/minute"

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def seeded_db():
    from pipeline.live import update_live_prices
    from pipeline.load import run_full_load

    run_full_load(offline=True)
    update_live_prices()
    return True


@pytest.fixture(scope="session")
def client(seeded_db):
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as c:
        yield c
