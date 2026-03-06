#!/usr/bin/env python3
"""
FastAPI dependencies — things that get injected into route functions.
Right now: database sessions. Later: Redis connections, auth, etc.
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
import os
from collections.abc import Generator

# ----------------- Third Party Library -----------------
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ----------------- Module-level Configuration -----------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/bma_alpha",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session, then closes it.
    FastAPI calls this via Depends(get_db) — one session per request.

    Why a generator?
    - The 'yield' gives the route a live session
    - The 'finally' guarantees cleanup even if the route crashes
    - FastAPI knows how to handle generator dependencies
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
