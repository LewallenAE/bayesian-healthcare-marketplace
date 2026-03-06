#!/usr/bin/env python3
"""
FastAPI application — the entry point.
Run with: uvicorn bma_alpha.api.main:app --reload
"""

# ----------------- Futures -----------------
from __future__ import annotations

# ----------------- Third Party Library -----------------
from fastapi import FastAPI

# ----------------- Application Imports -----------------
from bma_alpha.api.routes.ingest import router as ingest_router

# ----------------- App -----------------

app = FastAPI(
    title="Bayesian Healthcare Marketplace",
    version="0.1.0",
    description="Hierarchical Bayesian inference for healthcare pricing",
)

app.include_router(ingest_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
