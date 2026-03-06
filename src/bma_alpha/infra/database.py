#!/usr/bin/env python3
"""
SQLAlchemy ORM table definitions for the Bayesian Healthcare Marketplace.
Maps directly to the Postgres schema in the spec.
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Standard Library -----------------
from datetime import datetime, timezone
from uuid import uuid4

# ----------------- Third Party Library -----------------
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ----------------- Base -----------------

class Base(DeclarativeBase):
    """All ORM models inherit from this. Creates tables via Base.metadata.create_all()."""
    pass


# ----------------- Tables -----------------

class Provider(Base):
    """
    Healthcare providers — hospitals, clinics, specialists.
    One provider has many market events.
    """
    __tablename__ = "providers"

    id = Column(Uuid, primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    region = Column(Text, nullable=False)
    provider_type = Column(Text, nullable=False)          # "hospital", "clinic", "specialist"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: one provider → many events
    events = relationship("MarketEvent", back_populates="provider")


class MarketEvent(Base):
    """
    A single pricing event from a scraper/API/manual entry.
    This is the core table — every valid ingestion lands here.

    Key design decisions:
    - raw_payload (JSON): NEVER modified. You always keep the original messy data.
    - sanitized_price (Numeric): the cleaned Decimal from parse_money. NULL if validation failed.
    - idempotency_key (UNIQUE): prevents duplicate processing. Same key = 409 Conflict.
    - status: 'active' (normal), 'quarantined' (failed but stored), 'replayed' (recovered from DLQ).
    """
    __tablename__ = "market_events"

    id = Column(Uuid, primary_key=True, default=uuid4)
    provider_id = Column(Uuid, ForeignKey("providers.id"), nullable=False)
    idempotency_key = Column(Text, unique=True, nullable=False)
    raw_payload = Column(JSON, nullable=False)
    sanitized_price = Column(Numeric, nullable=True)      # NULL if validation failed
    service_type = Column(Text, nullable=False)            # "mri", "blood_panel", "consultation"
    patient_age = Column(Integer, nullable=True)           # missingness expected
    patient_risk = Column(Text, nullable=True)             # "low", "medium", "high"
    insurance_type = Column(Text, nullable=True)           # "medicare", "private", "uninsured"
    status = Column(Text, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: many events → one provider
    provider = relationship("Provider", back_populates="events")


class InferenceState(Base):
    """
    Snapshot of a Bayesian model's posterior for a given service type.
    New row per inference run — never overwritten, so you have full history.

    diagnostics (JSON): r_hat, ess, divergences, ppc_pvalue
    trace_artifact: file path to serialized ArviZ InferenceData
    """
    __tablename__ = "inference_states"

    id = Column(Uuid, primary_key=True, default=uuid4)
    service_type = Column(Text, nullable=False)
    model_version = Column(Text, nullable=False)           # "bayesian_v1", "rules_v1"
    mu = Column(Float, nullable=False)
    sigma = Column(Float, nullable=False)
    hdi_low = Column(Float, nullable=False)
    hdi_high = Column(Float, nullable=False)
    n_observations = Column(Integer, nullable=False)
    diagnostics = Column(JSON, nullable=False)
    trace_artifact = Column(Text, nullable=True)           # path to ArviZ trace
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class DeadLetterQueue(Base):
    """
    Quarantined events that failed validation.
    Replay-able: fix the schema/data, hit POST /dlq/{id}/replay, it re-enters ingestion.

    retry_count tracks how many times we've tried to replay this event.
    """
    __tablename__ = "dead_letter_queue"

    id = Column(Uuid, primary_key=True, default=uuid4)
    raw_payload = Column(JSON, nullable=False)
    error_type = Column(Text, nullable=False)              # "validation_error", "coercion_failure", "schema_mismatch"
    error_detail = Column(Text, nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)
    status = Column(Text, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class RulesBaseline(Base):
    """
    Percentile-based pricing — the 'dumb' baseline the Bayesian model beats.
    Exists so the /compare endpoint can show side-by-side divergence.
    """
    __tablename__ = "rules_baseline"

    id = Column(Uuid, primary_key=True, default=uuid4)
    service_type = Column(Text, nullable=False)
    percentile_25 = Column(Float, nullable=False)
    percentile_50 = Column(Float, nullable=False)
    percentile_75 = Column(Float, nullable=False)
    n_observations = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


# ----------------- Indexes -----------------
# These match the spec exactly. Postgres uses these for fast lookups.

Index("idx_idempotency", MarketEvent.idempotency_key, unique=True)
Index("idx_events_service_status", MarketEvent.service_type, MarketEvent.status)
Index("idx_events_provider_time", MarketEvent.provider_id, MarketEvent.created_at)
Index("idx_inference_service_version", InferenceState.service_type, InferenceState.model_version)
Index("idx_dlq_status", DeadLetterQueue.status, DeadLetterQueue.created_at)
