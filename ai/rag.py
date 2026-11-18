"""Lightweight retrieval over news.

Embeddings use a deterministic hashing vectorizer (unigrams + bigrams → 512 dims, L2-normalised) so the
project runs fully offline with zero model downloads. The storage contract (`News.embedding` = list[float])
is the same one a pgvector column uses, so swapping in a neural embedding model + `vector(512)` is a
one-function change (see docs/DECISIONS.md).
"""
from __future__ import annotations

import math
import re
import zlib
from datetime import timedelta

import numpy as np
from sqlalchemy import select

DIM = 512
TOKEN_RE = re.compile(r"[a-z0-9₹]+")
STOP = set("a an the of to in on for and or is are was were be by with at from as it its this that".split())


def _tokens(text: str) -> list[str]:
    words = [w for w in TOKEN_RE.findall(text.lower()) if w not in STOP]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]


def embed(text: str) -> list[float]:
    v = np.zeros(DIM, dtype=np.float32)
    for tok in _tokens(text):
        h = zlib.crc32(tok.encode())
        v[h % DIM] += 1.0 if (h >> 16) & 1 else -1.0  # signed hashing reduces collision bias
    n = float(np.linalg.norm(v))
    return [round(float(x / n), 5) for x in v] if n else v.tolist()


def search_news(query: str, asset_id: str | None = None, k: int = 5, days: int = 30) -> list[dict]:
    from core.db import News, session_scope
    from pipeline.load import utcnow

    with session_scope() as s:
        q = select(News).where(News.published >= utcnow() - timedelta(days=days))
        rows = s.execute(q).scalars().all()
    if asset_id:
        tagged = [r for r in rows if asset_id in (r.assets or "").split(",")]
        rows = tagged or rows
    if not rows:
        return []
    qv = np.array(embed(query))
    now = utcnow()
    scored = []
    for r in rows:
        if not r.embedding:
            continue
        sim = float(np.dot(qv, np.array(r.embedding)))
        age_days = max((now - r.published).total_seconds() / 86400, 0)
        recency = math.exp(-age_days / 10)  # newer news matters more for "why did X move this week"
        tag_bonus = 0.15 if asset_id and asset_id in (r.assets or "") else 0
        scored.append((0.7 * sim + 0.3 * recency + tag_bonus, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"title": r.title, "summary": r.summary, "link": r.link, "source": r.source,
             "published": r.published.isoformat(), "score": round(sc, 3)} for sc, r in scored[:k]]
