#!/usr/bin/env python3
"""
 Enter module docstring here
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# ----------------- Third Party Library -----------------
from pydantic import BaseModel, ConfigDict, field_validator

# ----------------- Application Imports -----------------
from bma_alpha.core.money import parse_money

# ----------------- Module-level Configuration -----------------


class EventIngestPayload(BaseModel):
    """
    Raw inbound payload from scrapers / partner APIs / manual entry.
    This is the UNTRUSTED input — messy strings, missing fields, duplicates.
    Pydantic validates and coerces BEFORE anything touches the database.
    """

    model_config = ConfigDict(
        strict=False,           # allow coercion (str → Decimal, str → int)
        str_strip_whitespace=True,  # auto-strip " MRI " → "MRI"
    )

    # --- Required fields ---
    idempotency_key: str                    # caller-generated unique key, prevents duplicate processing
    provider_id: UUID                       # which provider sent this event
    service_type: str                       # "MRI", "blood_panel", "consultation"
    raw_price: str                          # messy string like "$1,250.00" or "Free"

    # --- Optional fields (missingness is expected in healthcare data) ---
    patient_age: int | None = None          # nullable — uninsured patients often skip intake forms
    patient_risk: str | None = None         # "low", "medium", "high" — nullable
    insurance_type: str | None = None       # "medicare", "private", "uninsured" — nullable

    # --- Computed after validation ---
    sanitized_price: Decimal | None = None  # filled by validator below; None = validation failed

    @field_validator("raw_price", mode="before")
    @classmethod
    def coerce_raw_price_string(cls, v: object) -> str:
        """Ensure raw_price arrives as a string so parse_money can handle it."""
        if v is None:
            raise ValueError("raw_price must not be None")
        return str(v)

    @field_validator("service_type", mode="after")
    @classmethod
    def normalize_service_type(cls, v: str) -> str:
        """Lowercase + underscore normalization: 'Blood Panel' → 'blood_panel'."""
        return v.strip().lower().replace(" ", "_")

    @field_validator("patient_risk", mode="after")
    @classmethod
    def validate_patient_risk(cls, v: str | None) -> str | None:
        if v is None:
            return None
        allowed = {"low", "medium", "high"}
        normalized = v.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"patient_risk must be one of {allowed}, got {v!r}")
        return normalized

    def model_post_init(self, __context: object) -> None:
        try:
            self.sanitized_price = parse_money(self.raw_price)
        except (ValueError, TypeError):
            self.sanitized_price = None

    @field_validator("insurance_type", mode="after")
    @classmethod
    def validate_insurance_type(cls, insurance: str | None) -> str | None:
        if insurance is None:
            return None
        ins_allowed = {"medicare", "medicaid", "private", "uninsured"}
        ins_normalized = insurance.strip().lower()
        if ins_normalized not in ins_allowed:
            raise ValueError(f"insurance_type must be one of the following: {ins_allowed} got {insurance!r}")
        return ins_normalized
    
class DLQEntry(BaseModel):
    """
    A dead letter queue. When sanitized_price is None (parse faield), the ingestion service creates a DLQEntry and writes it to Postgres.
    """
    raw_payload: dict # JSON body failed stored as JSONB
    error_type: str # Either validation_error, coercion_failure, or schema_mismatch
    error_detail: str # the actual error message
    retry_count: int = 0 # Default of 0
    status: str = "pending" # Default pending, allowed: pending, replayed, discarded

    @field_validator("error_type", mode="after")
    @classmethod
    def validate_error_type(cls, v:str) -> str:
        allowed = {"validation_error", "coercion_failure", "schema_mismatch"}
        normalized = v.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"error_type must be one of the following: {allowed} got {v!r}")
        return normalized
    
    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v:str) -> str:
        allowed = {"pending", "replayed", "discarded"}
        normalized = v.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"status must be one of the following: {allowed} got {v!r}")
        return normalized
