"""News ingestion for RAG: RSS → tag by asset → embed → store."""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from ai.rag import embed
from core.db import News, session_scope
from pipeline.assets import ASSETS
from pipeline.load import utcnow

log = logging.getLogger("wealthlens.news")

FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "ET Commodities": "https://economictimes.indiatimes.com/markets/commodities/rssfeeds/1808152121.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/marketreports.xml",
    "Livemint": "https://www.livemint.com/rss/markets",
}
TAG_RE = re.compile(r"<[^>]+>")


def tag_assets(text: str) -> list[str]:
    t = text.lower()
    return [a.id for a in ASSETS if any(k in t for k in a.keywords)]


def ingest_news(max_age_days: int = 30) -> int:
    import feedparser

    added = 0
    with session_scope() as s:
        known = set(s.execute(select(News.link)).scalars().all())
        for source, url in FEEDS.items():
            try:
                feed = feedparser.parse(url, agent="WealthLens/1.0 (educational project)")
            except Exception as e:
                log.warning("Feed %s failed: %s", source, e)
                continue
            for e in feed.entries[:60]:
                link = e.get("link")
                if not link or link in known:
                    continue
                title = html.unescape(e.get("title", "")).strip()
                summary = html.unescape(TAG_RE.sub("", e.get("summary", ""))).strip()[:800]
                pub = e.get("published_parsed") or e.get("updated_parsed")
                published = datetime(*pub[:6]) if pub else utcnow()
                s.add(News(title=title, summary=summary, link=link, source=source, published=published,
                           assets=",".join(tag_assets(f"{title} {summary}")),
                           embedding=embed(f"{title}. {summary}")))
                known.add(link)
                added += 1
        s.execute(delete(News).where(News.published < utcnow() - timedelta(days=max_age_days)))
    log.info("News: %d new articles", added)
    return added
