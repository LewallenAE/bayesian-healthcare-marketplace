#!/usr/bin/env python3
"""
Tests for EventIngestPayload and DLQEntry domain models.
These test Pydantic validation ONLY — no database, no HTTP.
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
from decimal import Decimal
from uuid import uuid4

# ----------------- Third Party Library -----------------
import pytest
from pydantic import ValidationError

# ----------------- Application Imports -----------------
from bma_alpha.domain.EventIngest import EventIngestPayload, DLQEntry


# --------------------- EventIngestPayload ---------------------------

# A valid base payload we can copy and modify per test
VALID_PAYLOAD = {
    "idempotency_key": "test-key-001",
    "provider_id": str(uuid4()),
    "service_type": "MRI",
    "raw_price": "$1,250.00",
}


class TestEventIngestPayloadValid:
    """Happy path — things that SHOULD work."""

    def test_basic_valid_payload(self):
        p = EventIngestPayload(**VALID_PAYLOAD)
        assert p.sanitized_price == Decimal("1250.00")
        assert p.service_type == "mri"              # normalized to lowercase

    def test_free_consultation(self):
        payload = {**VALID_PAYLOAD, "raw_price": "Free consultation"}
        p = EventIngestPayload(**payload)
        assert p.sanitized_price == Decimal("0.00")

    def test_tilde_price(self):
        payload = {**VALID_PAYLOAD, "raw_price": "~800"}
        p = EventIngestPayload(**payload)
        assert p.sanitized_price == Decimal("800.00")

    def test_service_type_normalization(self):
        payload = {**VALID_PAYLOAD, "service_type": "Blood Panel"}
        p = EventIngestPayload(**payload)
        assert p.service_type == "blood_panel"

    def test_optional_fields_default_none(self):
        p = EventIngestPayload(**VALID_PAYLOAD)
        assert p.patient_age is None
        assert p.patient_risk is None
        assert p.insurance_type is None

    def test_optional_fields_provided(self):
        payload = {
            **VALID_PAYLOAD,
            "patient_age": 45,
            "patient_risk": "High",         # should normalize to "high"
            "insurance_type": "Medicare",    # should normalize to "medicare"
        }
        p = EventIngestPayload(**payload)
        assert p.patient_age == 45
        assert p.patient_risk == "high"
        assert p.insurance_type == "medicare"

    def test_string_age_coerced(self):
        """strict=False means "25" → 25."""
        payload = {**VALID_PAYLOAD, "patient_age": "25"}
        p = EventIngestPayload(**payload)
        assert p.patient_age == 25


class TestEventIngestPayloadInvalid:
    """Things that SHOULD fail."""

    def test_unparseable_price_sets_none(self):
        """N/A can't be parsed — sanitized_price should be None (DLQ candidate)."""
        payload = {**VALID_PAYLOAD, "raw_price": "N/A"}
        p = EventIngestPayload(**payload)
        assert p.sanitized_price is None

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            EventIngestPayload(
                idempotency_key="key",
                provider_id=str(uuid4()),
                # missing service_type and raw_price
            )

    def test_bad_patient_risk_raises(self):
        payload = {**VALID_PAYLOAD, "patient_risk": "extreme"}
        with pytest.raises(ValidationError):
            EventIngestPayload(**payload)

    def test_bad_insurance_type_raises(self):
        payload = {**VALID_PAYLOAD, "insurance_type": "gold_plan"}
        with pytest.raises(ValidationError):
            EventIngestPayload(**payload)

    def test_null_raw_price_raises(self):
        payload = {**VALID_PAYLOAD, "raw_price": None}
        with pytest.raises(ValidationError):
            EventIngestPayload(**payload)


# --------------------- DLQEntry ---------------------------

class TestDLQEntry:

    def test_valid_dlq_entry(self):
        entry = DLQEntry(
            raw_payload={"bad": "data"},
            error_type="validation_error",
            error_detail="missing field: service_type",
        )
        assert entry.retry_count == 0
        assert entry.status == "pending"

    def test_error_type_normalized(self):
        entry = DLQEntry(
            raw_payload={},
            error_type="  COERCION_FAILURE  ",
            error_detail="test",
        )
        assert entry.error_type == "coercion_failure"

    def test_bad_error_type_raises(self):
        with pytest.raises(ValidationError):
            DLQEntry(
                raw_payload={},
                error_type="unknown_error",
                error_detail="test",
            )

    def test_bad_status_raises(self):
        with pytest.raises(ValidationError):
            DLQEntry(
                raw_payload={},
                error_type="validation_error",
                error_detail="test",
                status="deleted",
            )
