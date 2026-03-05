# Bayesian Healthcare Marketplace Engine — Progress

## Current Status
**Week:** 1 of 6 — Ingestion Pipeline + Data Generator
**Active Task:** Step 3 — Unit tests for `parse_money`
**Last Updated:** 2026-03-05

---

## Week 1-2: Ingestion Pipeline + Data Generator

### Milestone 1 — Project Scaffolding + Core Parsing
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 1 | `pyproject.toml` + dependencies + tooling | **Done** | 0.5 |
| 2 | Money parser — `parse_money()` with Decimal, ROUND_HALF_UP, garbage rejection | **Done** | 1 |
| 3 | Unit tests for `parse_money` (parametrized valid + invalid) | **Next** | 1 |
| 4 | Domain event model — `MarketplaceEvent` (Pydantic V2, frozen, strict, forbid extras) | Not Started | 2 |
| 5 | Unit tests for domain model | Not Started | 1 |
| 6 | Minimal FastAPI app + `GET /health` | Not Started | 0.5 |

### Milestone 2 — Database + Ingestion Endpoint
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 7 | Postgres schema — `providers`, `market_events`, `inference_states`, `dead_letter_queue`, `rules_baseline` | Not Started | 2 |
| 8 | SQLAlchemy table definitions + Alembic initial migration | Not Started | 3 |
| 9 | `POST /api/v1/events/ingest` — strict validation, idempotency on `idempotency_key` | Not Started | 4 |
| 10 | DLQ routing — validation failures quarantined with full error trace | Not Started | 3 |
| 11 | `GET /api/v1/dlq` + `POST /api/v1/dlq/{id}/replay` + batch replay | Not Started | 3 |
| 12 | Redis + Celery skeleton — task dispatch on successful ingest | Not Started | 3 |
| 13 | Integration tests — idempotency, DLQ routing, replay cycle | Not Started | 3 |

### Milestone 3 — Synthetic Data Generator
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 14 | Generator core — produces `market_event`-shaped payloads | Not Started | 3 |
| 15 | MNAR missingness (age missing for uninsured, insurance missing for out-of-network) | Not Started | 2 |
| 16 | Right-censoring + interval-censoring for claims | Not Started | 2 |
| 17 | Selection bias (healthier patients overrepresented) | Not Started | 2 |
| 18 | Simpson's paradox scenario (toggle on/off) | Not Started | 2 |
| 19 | `POST /api/v1/dev/generate` endpoint | Not Started | 1 |
| 20 | Tests — pathology verification, output shape validation | Not Started | 2 |

**Week 1-2 Done Criteria:**
- [x] `ruff check .` passes
- [x] `pytest -q` runs (no errors)
- [x] Money parsing is Decimal-based, ROUND_HALF_UP, tested
- [ ] Domain model is strict + immutable + tested
- [ ] FastAPI boots and `/health` returns OK
- [ ] POST 5,000 synthetic events with 15% missingness and 8% censoring
- [ ] Clean events land in `market_events`, messy ones in `dead_letter_queue`
- [ ] Replay quarantined events successfully after schema correction
- [ ] Celery dispatches `update_posterior` task on ingest (task is a no-op stub for now)

**Subtotal: ~35 hours | Completed: ~1.5 hours**

---

## Week 3-4: Bayesian Models + Diagnostics

### Milestone 4 — Hierarchical Pricing Model
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 21 | PyMC hierarchical model — provider + region random effects, CMS-informed priors | Not Started | 8 |
| 22 | Cold start handling — wide priors with explicit uncertainty when n < 10 | Not Started | 2 |
| 23 | Missing data via prior predictive imputation (not mean imputation) | Not Started | 3 |
| 24 | `update_posterior` Celery task — NUTS sampling, 2000 draws, 4 chains | Not Started | 4 |
| 25 | ADVI fallback if MCMC fails to converge within 120s timeout | Not Started | 2 |
| 26 | Tests — convergence on known synthetic data, cold start behavior | Not Started | 3 |

### Milestone 5 — Insurance Risk GLM + Rules Baseline
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 27 | Two-part Bayesian GLM — claim probability (logistic) + severity (Gamma) | Not Started | 5 |
| 28 | Censored claims likelihood adjustment | Not Started | 3 |
| 29 | Rules-based baseline engine — percentile calculations per service type | Not Started | 2 |
| 30 | Tests — risk score outputs, baseline percentile correctness | Not Started | 2 |

### Milestone 6 — Diagnostics + Inference API
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 31 | Diagnostics module — R-hat, ESS, divergence checks, PPC evaluators | Not Started | 4 |
| 32 | Health status reporter — "healthy" / "warning" / "unhealthy" with reasons | Not Started | 2 |
| 33 | `GET /api/v1/inference/{service_type}` — posterior summary + HDI | Not Started | 2 |
| 34 | `GET /api/v1/compare/{service_type}` — Bayesian vs rules side-by-side | Not Started | 2 |
| 35 | `GET /api/v1/diagnostics/{service_type}` — full model health report | Not Started | 2 |
| 36 | Tests — diagnostics thresholds, API response schemas | Not Started | 2 |

**Week 3-4 Done Criteria:**
- [ ] `GET /inference/MRI` returns posterior summary with HDI after ingesting synthetic data
- [ ] `GET /compare/MRI` shows Bayesian vs rules side-by-side with divergence magnitude
- [ ] `GET /diagnostics/MRI` returns green health status with all checks passing
- [ ] Insurance risk model produces risk scores with credible intervals
- [ ] ADVI fallback triggers correctly when MCMC times out

**Subtotal: ~45 hours**

---

## Week 5-6: Counterfactuals + Elasticity + Dashboard

### Milestone 7 — Elasticity Model + Counterfactual Engine
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 37 | Supply-demand elasticity model — log-linear demand, Poisson likelihood | Not Started | 5 |
| 38 | Counterfactual engine — clone data, apply scenario mods, re-run inference | Not Started | 6 |
| 39 | `run_counterfactual` Celery task — abbreviated MCMC (1000 draws, 2 chains) | Not Started | 3 |
| 40 | `POST /api/v1/simulate/counterfactual` endpoint | Not Started | 3 |
| 41 | Tests — scenario correctness, delta distribution shape, revenue impact bounds | Not Started | 3 |

### Milestone 8 — React Dashboard
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 42 | React project scaffolding + API client | Not Started | 2 |
| 43 | Page 1: Marketplace Intelligence — price table, Bayesian vs rules chart, counterfactual panel, elasticity curves | Not Started | 10 |
| 44 | Page 2: Operations Console — DLQ browser, replay controls, diagnostics panel, activity feed | Not Started | 8 |
| 45 | Plotly integration — posterior distributions, uncertainty bands, counterfactual deltas | Not Started | 4 |

### Milestone 9 — Deployment + Polish
| # | Task | Status | Est. Hours |
|---|------|--------|------------|
| 46 | Docker Compose — API + Postgres + Redis + Celery worker | Not Started | 3 |
| 47 | Deploy to Railway/Fly.io | Not Started | 2 |
| 48 | End-to-end smoke test on deployed URL | Not Started | 1 |

**Week 5-6 Done Criteria:**
- [ ] Counterfactual simulation returns baseline vs modified HDI with revenue impact distribution
- [ ] Dashboard shows live price intelligence with health indicators
- [ ] DLQ browsing and replay works from the UI
- [ ] Full stack runs with `docker compose up`
- [ ] Deployed to a shareable URL

**Subtotal: ~50 hours**

---

## Total: ~130 hours | Completed: ~1.5 hours (1%)

---

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-04 | Project kickoff | Build Bayesian marketplace engine as portfolio piece for Senior Marketplace Quant roles |
| 2026-03-04 | Healthcare domain | Directly mirrors General Medicine role — providers, patients, insurance, CMS priors |
| 2026-03-04 | Decimal-only money | IEEE 754 rounding errors compound in posterior calculations |
| 2026-03-04 | React over Streamlit | Production signal — React frontend says "I ship products", Streamlit says "I make demos" |
| 2026-03-04 | Synthetic data generator as first-class module | Demonstrates understanding of real data pathologies, not just modeling on clean data |
| 2026-03-05 | Full spec, not accelerated | Full system is the strongest interview signal; can delegate boilerplate to AI tooling |

---

## Blockers
_None currently._
