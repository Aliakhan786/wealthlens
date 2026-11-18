"""Database engine, session factory and ORM models (shared by pipeline, backend and AI)."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from core.config import get_settings

settings = get_settings()

if settings.is_sqlite:
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):  # WAL = concurrent reads while the scheduler writes
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()
else:
    # Connection pooling for Postgres (Supabase / Neon)
    engine = create_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # slug, e.g. "gold"
    name: Mapped[str] = mapped_column(String(160))
    asset_class: Mapped[str] = mapped_column(String(30))  # commodity | index | etf | mutual_fund | fx
    symbol: Mapped[str] = mapped_column(String(60))
    source: Mapped[str] = mapped_column(String(30))  # yfinance | mfapi | derived
    unit: Mapped[str] = mapped_column(String(40), default="INR")
    description: Mapped[str] = mapped_column(Text, default="")
    risk_category: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    first_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PriceDaily(Base):
    __tablename__ = "prices_daily"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_prices_daily_asset_date", "asset_id", "date"),)


class PriceLive(Base):
    __tablename__ = "prices_live"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    price: Mapped[float] = mapped_column(Float)
    prev_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    change: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime)


class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshot"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime)
    payload: Mapped[dict] = mapped_column(JSON)


class Macro(Base):
    __tablename__ = "macro"
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpi_inflation: Mapped[float] = mapped_column(Float)  # % y/y
    fd_rate: Mapped[float] = mapped_column(Float)  # % 1-year FD (indicative)


class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(600), unique=True)
    source: Mapped[str] = mapped_column(String(80))
    published: Mapped[datetime] = mapped_column(DateTime)
    assets: Mapped[str] = mapped_column(String(300), default="")  # comma-separated asset ids
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
