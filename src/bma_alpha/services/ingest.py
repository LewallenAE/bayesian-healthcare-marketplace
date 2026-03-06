#!/usr/bin/env python3
"""
Ingestion service — the orchestrator between Pydantic validation and Postgres writes.

Flow:
  1. Raw JSON arrives
  2. Try to parse it into EventIngestPayload (Pydantic validates + coerces)
  3. If Pydantic rejects it entirely → DLQ with error_type="validation_error"
  4. If Pydantic accepts but sanitized_price is None → DLQ with error_type="coercion_failure"
  5. If sanitized_price is valid → check idempotency → write to market_events
  6. Duplicate idempotency_key → return 409
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
from dataclasses import dataclass
from enum import Enum

# ----------------- Third Party Library -----------------
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# ----------------- Application Imports -----------------
from bma_alpha.domain.EventIngest import EventIngestPayload, DLQEntry
from bma_alpha.infra.database import MarketEvent, DeadLetterQueue


# ----------------- Result types -----------------
# These tell the caller (FastAPI route) WHAT happened so it can pick the right HTTP status.

class IngestOutcome(str, Enum):
    CREATED = "created"             # 201 — event stored in market_events
    DUPLICATE = "duplicate"         # 409 — idempotency_key already exists
    QUARANTINED = "quarantined"     # 202 — sent to DLQ


@dataclass
class IngestResult:
    outcome: IngestOutcome
    event_id: str | None = None     # UUID of the market_event (if created)
    dlq_id: str | None = None       # UUID of the DLQ entry (if quarantined)
    error: str | None = None        # error message (if quarantined or duplicate)


# ----------------- Service -----------------

def ingest_event(raw_payload: dict, db: Session) -> IngestResult:
    """
    Main entry point. Takes raw JSON dict + a database session.
    Returns an IngestResult telling the caller what happened.

    This function does NOT raise exceptions for business logic —
    it catches them and returns structured results.
    """

    # --- Step 1: Pydantic validation ---
    # If the payload is so broken Pydantic can't even parse it,
    # we catch ValidationError and route to DLQ immediately.
    try:
        payload = EventIngestPayload(**raw_payload)
    except ValidationError as e:
        return _quarantine(
            raw_payload=raw_payload,
            error_type="validation_error",
            error_detail=str(e),
            db=db,
        )

    # --- Step 2: Check if parse_money succeeded ---
    # Pydantic accepted the shape, but model_post_init might have
    # set sanitized_price = None (meaning parse_money failed).
    if payload.sanitized_price is None:
        return _quarantine(
            raw_payload=raw_payload,
            error_type="coercion_failure",
            error_detail=f"Could not parse raw_price: {payload.raw_price!r}",
            db=db,
        )

    # --- Step 3: Write to market_events with idempotency guard ---
    event = MarketEvent(
        provider_id=payload.provider_id,
        idempotency_key=payload.idempotency_key,
        raw_payload=raw_payload,
        sanitized_price=payload.sanitized_price,
        service_type=payload.service_type,
        patient_age=payload.patient_age,
        patient_risk=payload.patient_risk,
        insurance_type=payload.insurance_type,
        status="active",
    )

    try:
        db.add(event)
        db.commit()
    except IntegrityError:
        db.rollback()
        return IngestResult(
            outcome=IngestOutcome.DUPLICATE,
            error=f"Duplicate idempotency_key: {payload.idempotency_key!r}",
        )

    return IngestResult(
        outcome=IngestOutcome.CREATED,
        event_id=str(event.id),
    )


# ----------------- Internal helpers -----------------

def _quarantine(
    raw_payload: dict,
    error_type: str,
    error_detail: str,
    db: Session,
) -> IngestResult:
    """Write a failed event to the dead_letter_queue and return a quarantine result."""

    dlq_row = DeadLetterQueue(
        raw_payload=raw_payload,
        error_type=error_type,
        error_detail=error_detail,
    )
    db.add(dlq_row)
    db.commit()

    return IngestResult(
        outcome=IngestOutcome.QUARANTINED,
        dlq_id=str(dlq_row.id),
        error=error_detail,
    )
