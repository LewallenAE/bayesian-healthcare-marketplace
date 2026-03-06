#!/usr/bin/env python3
"""
Tests for the ingestion service — business logic layer.
Uses in-memory SQLite via the db fixture from conftest.py.
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
from uuid import uuid4

# ----------------- Third Party Library -----------------
import pytest

# ----------------- Application Imports -----------------
from bma_alpha.services.ingest import IngestOutcome, ingest_event
from bma_alpha.infra.database import MarketEvent, DeadLetterQueue


# --------------------- Helpers ---------------------------

def make_payload(**overrides) -> dict:
    """Build a valid payload, overriding specific fields for each test."""
    base = {
        "idempotency_key": str(uuid4()),    # unique per call
        "provider_id": str(uuid4()),
        "service_type": "MRI",
        "raw_price": "$1,250.00",
    }
    base.update(overrides)
    return base


# --------------------- Happy Path ---------------------------

class TestIngestCreated:

    def test_valid_event_creates_market_event(self, db):
        result = ingest_event(make_payload(), db)
        assert result.outcome == IngestOutcome.CREATED
        assert result.event_id is not None

        # Verify it's actually in the database
        count = db.query(MarketEvent).count()
        assert count == 1

    def test_created_event_has_correct_fields(self, db):
        payload = make_payload(
            service_type="Blood Panel",
            raw_price="$99.50",
            patient_age=30,
            patient_risk="low",
        )
        result = ingest_event(payload, db)
        event = db.query(MarketEvent).first()

        assert event.service_type == "blood_panel"     # normalized
        assert float(event.sanitized_price) == 99.50
        assert event.patient_age == 30
        assert event.patient_risk == "low"
        assert event.status == "active"


# --------------------- Idempotency ---------------------------

class TestIngestDuplicate:

    def test_duplicate_key_returns_409(self, db):
        key = "same-key-twice"
        ingest_event(make_payload(idempotency_key=key), db)
        result = ingest_event(make_payload(idempotency_key=key), db)

        assert result.outcome == IngestOutcome.DUPLICATE
        assert "Duplicate" in result.error

        # Only one row in database
        count = db.query(MarketEvent).count()
        assert count == 1


# --------------------- DLQ Routing ---------------------------

class TestIngestQuarantined:

    def test_unparseable_price_goes_to_dlq(self, db):
        result = ingest_event(make_payload(raw_price="N/A"), db)
        assert result.outcome == IngestOutcome.QUARANTINED
        assert result.dlq_id is not None

        # Verify DLQ entry
        dlq = db.query(DeadLetterQueue).first()
        assert dlq.error_type == "coercion_failure"

    def test_missing_required_field_goes_to_dlq(self, db):
        bad_payload = {"raw_price": "$100"}  # missing idempotency_key, provider_id, service_type
        result = ingest_event(bad_payload, db)
        assert result.outcome == IngestOutcome.QUARANTINED
        assert result.dlq_id is not None

        dlq = db.query(DeadLetterQueue).first()
        assert dlq.error_type == "validation_error"

    def test_quarantined_event_not_in_market_events(self, db):
        ingest_event(make_payload(raw_price="N/A"), db)
        assert db.query(MarketEvent).count() == 0
        assert db.query(DeadLetterQueue).count() == 1
