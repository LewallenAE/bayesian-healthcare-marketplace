#!/usr/bin/env python3
"""
POST /api/v1/events/ingest

Thin HTTP layer. All business logic lives in services/ingest.py.
This route only does three things:
  1. Receive the JSON body
  2. Call ingest_event()
  3. Map the IngestOutcome to an HTTP status code
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Third Party Library -----------------
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# ----------------- Application Imports -----------------
from bma_alpha.api.dependencies import get_db
from bma_alpha.services.ingest import IngestOutcome, ingest_event

# ----------------- Router -----------------

router = APIRouter(prefix="/api/v1/events", tags=["ingestion"])


@router.post("/ingest")
def ingest(body: dict, db: Session = Depends(get_db)) -> JSONResponse:
    """
    Accepts a raw pricing event payload.

    Returns:
      201 Created     — event stored in market_events
      409 Conflict    — duplicate idempotency_key
      202 Accepted    — quarantined to DLQ (bad data, but we kept it)
    """
    result = ingest_event(raw_payload=body, db=db)

    if result.outcome == IngestOutcome.CREATED:
        return JSONResponse(
            status_code=201,
            content={"status": "created", "event_id": result.event_id},
        )

    if result.outcome == IngestOutcome.DUPLICATE:
        return JSONResponse(
            status_code=409,
            content={"status": "duplicate", "error": result.error},
        )

    # QUARANTINED
    return JSONResponse(
        status_code=202,
        content={
            "status": "quarantined",
            "dlq_id": result.dlq_id,
            "error": result.error,
        },
    )
