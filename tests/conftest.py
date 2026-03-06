#!/usr/bin/env python3
"""
Shared test fixtures.

Key idea: tests use an IN-MEMORY SQLite database, not real Postgres.
This means tests are fast, isolated, and don't need Docker running.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bma_alpha.infra.database import Base


@pytest.fixture()
def db():
    """
    Creates a fresh in-memory database for each test.

    Why per-test?
    - Each test starts with empty tables — no leftover data from other tests
    - Tests can run in any order and still pass
    - This is called 'test isolation'
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
