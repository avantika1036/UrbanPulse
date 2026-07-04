"""
backend/database.py

SQLAlchemy engine and session setup for UrbanPulse. Synchronous engine
(not async) — simpler to reason about and sufficient for this project's
read-heavy, modest-concurrency workload.

DATABASE_URL is read from the environment, with a local-dev fallback.
All tables live under the 'urbanpulse' PostgreSQL schema (see sql/schema.sql).

Usage in a FastAPI route:
    from backend.database import get_db
    from fastapi import Depends

    @router.get("/cities")
    def list_cities(db: Session = Depends(get_db)):
        return db.query(City).all()
"""

import os

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base

# ── DATABASE URL ─────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/urbanpulse")

SCHEMA_NAME = "urbanpulse"

# ── ENGINE ───────────────────────────────────────────────────────────────────

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # detects and recovers from stale/dropped connections
    future=True,
)

# ── SESSION FACTORY ──────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# ── DECLARATIVE BASE ─────────────────────────────────────────────────────────
# All ORM models (backend/models.py) target the 'urbanpulse' schema by
# setting __table_args__ = {"schema": "urbanpulse"} on each model, so the
# metadata here doesn't need a schema= override at the Base level — each
# model declares it explicitly for clarity and to match sql/schema.sql 1:1.

Base = declarative_base()


def get_db():
    """
    FastAPI dependency generator — yields a SQLAlchemy Session and
    guarantees it is closed after the request completes, even if an
    exception is raised mid-request.

    Usage:
        @router.get("/cities")
        def list_cities(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all():
    """
    Creates all tables defined on Base.metadata if they don't already
    exist. Intended for local development convenience only — in
    production, schema changes should go through sql/schema.sql and a
    proper migration tool, not create_all().

    Note: this does NOT create the 'urbanpulse' schema itself if it
    doesn't exist — run sql/schema.sql first (which includes
    CREATE SCHEMA IF NOT EXISTS urbanpulse;), or uncomment the
    CREATE SCHEMA statement below for a fully self-contained dev setup.
    """
    with engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}")
        )
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print(f"[database] create_all() complete — all tables ensured in schema '{SCHEMA_NAME}'.")


if __name__ == "__main__":
    print(f"[database] DATABASE_URL: {DATABASE_URL}")
    print(f"[database] Schema: {SCHEMA_NAME}")
    print("[database] Running create_all() for local dev setup...")
    create_all()