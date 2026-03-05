# Bayesian Healthcare Marketplace Engine — Project Spec

**Target Role:** Senior Marketplace Quant — General Medicine (SF/Boston hybrid, $180k–$220k)
**Author:** Anthony
**Status:** Ready to Start — Module 1

---

## Mission

Build a production-grade Bayesian inference system for healthcare marketplace pricing that demonstrates: hierarchical probabilistic modeling on messy/incomplete data, production engineering discipline (DLQ, idempotency, async workers), model self-awareness (diagnostics as a service), and the ability to run real counterfactual simulations a Chief Economist would trust.

This is not a notebook. This is a deployable system.

---

## What It Does

Healthcare pricing events arrive asynchronously from scrapers, partner APIs, or manual entry — messy, incomplete, and irregular. The system:

1. **Ingests and validates** raw pricing events through strict schema enforcement, quarantining failures to a Dead Letter Queue with full traceability.
2. **Stores** raw and sanitized events in Postgres with idempotency guarantees — no duplicate processing, no silent data loss.
3. **Infers** true market prices and insurance risk via hierarchical Bayesian models that capture patient-level, provider-level, and regional heterogeneity — not averages, not point estimates, but calibrated posterior distributions with credible intervals.
4. **Compares** Bayesian model outputs against a rules-based pricing engine side-by-side, directly demonstrating the transition from heuristic to probabilistic systems.
5. **Simulates** counterfactual scenarios ("What happens to marketplace revenue if we restrict high-risk patients from premium providers?") by running full posterior simulations under modified assumptions.
6. **Monitors its own health** — convergence diagnostics, effective sample sizes, and prior predictive checks are exposed via API, not buried in notebooks.

---

## Why It Screams Senior

| Senior Signal | How This Project Proves It |
|---|---|
| Deep Bayesian modeling | Hierarchical models with patient/provider/region random effects, proper priors, MCMC sampling, HDI quantification |
| Messy real-world data | Synthetic data generator with configurable missingness, censoring, selection bias, Simpson's paradox scenarios |
| Production reliability | Idempotency keys, DLQ with replay, Pydantic V2 strict validation, transactional writes, async MCMC via Redis workers |
| Model self-awareness | Diagnostics API exposing R-hat, ESS, divergence counts, prior/posterior predictive checks — the system knows when it's wrong |
| Rules-to-Bayesian transition | Side-by-side comparison endpoint showing where heuristic pricing diverges from calibrated posteriors — mirrors the exact work this role hires for |
| Counterfactual rigor | Full posterior simulation under policy changes, not toy sensitivity analysis — returns revenue impact distributions with credible intervals |
| Cross-functional translation | React dashboard with interactive Plotly charts designed for a non-technical Chief Economist audience |
| Supply-demand intuition | Bayesian elasticity model connecting pricing to utilization, replacing a standalone matching engine with tighter marketplace logic |

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Bayesian modeling | PyMC 5 + ArviZ | Hierarchical models, NUTS sampler, built-in diagnostics |
| API | FastAPI + Pydantic V2 | Strict validation, async support, extends existing webhook relay experience |
| Database | PostgreSQL | ACID transactions, proper indexing, JSONB for raw payloads |
| Task queue | Redis + Celery | Offload blocking MCMC sampling from web thread |
| Frontend | React + Plotly.js | Production signal over Streamlit; clean API consumption pattern |
| Deployment | Docker + Railway/Fly.io | One-click deploy, reproducible environments |
| Testing | Pytest + hypothesis | Property-based testing for data generator, integration tests with real posterior checks |

---

## Database Schema

### Tables

**providers**
```
id              UUID PRIMARY KEY
name            TEXT NOT NULL
region          TEXT NOT NULL
provider_type   TEXT NOT NULL          -- e.g., "hospital", "clinic", "specialist"
created_at      TIMESTAMPTZ DEFAULT now()
```

**market_events**
```
id              UUID PRIMARY KEY
provider_id     UUID REFERENCES providers(id)
idempotency_key TEXT UNIQUE NOT NULL
raw_payload     JSONB NOT NULL         -- original messy data, never modified
sanitized_price NUMERIC               -- NULL if validation failed
service_type    TEXT NOT NULL          -- e.g., "MRI", "blood_panel", "consultation"
patient_age     INTEGER               -- nullable (missingness is expected)
patient_risk    TEXT                   -- nullable
insurance_type  TEXT                   -- nullable
status          TEXT DEFAULT 'active'  -- 'active', 'quarantined', 'replayed'
created_at      TIMESTAMPTZ DEFAULT now()
```

**inference_states**
```
id              UUID PRIMARY KEY
service_type    TEXT NOT NULL
model_version   TEXT NOT NULL          -- "bayesian_v1", "rules_v1", etc.
mu              FLOAT NOT NULL
sigma           FLOAT NOT NULL
hdi_low         FLOAT NOT NULL
hdi_high        FLOAT NOT NULL
n_observations  INTEGER NOT NULL
diagnostics     JSONB NOT NULL         -- r_hat, ess, divergences, ppc_pvalue
trace_artifact  TEXT                   -- path to serialized trace (ArviZ InferenceData)
updated_at      TIMESTAMPTZ DEFAULT now()
```

**dead_letter_queue**
```
id              UUID PRIMARY KEY
raw_payload     JSONB NOT NULL
error_type      TEXT NOT NULL          -- 'validation_error', 'coercion_failure', 'schema_mismatch'
error_detail    TEXT NOT NULL
retry_count     INTEGER DEFAULT 0
status          TEXT DEFAULT 'pending' -- 'pending', 'replayed', 'discarded'
created_at      TIMESTAMPTZ DEFAULT now()
resolved_at     TIMESTAMPTZ
```

**rules_baseline**
```
id              UUID PRIMARY KEY
service_type    TEXT NOT NULL
percentile_25   FLOAT NOT NULL
percentile_50   FLOAT NOT NULL
percentile_75   FLOAT NOT NULL
n_observations  INTEGER NOT NULL
updated_at      TIMESTAMPTZ DEFAULT now()
```

### Indexes
```sql
CREATE UNIQUE INDEX idx_idempotency ON market_events(idempotency_key);
CREATE INDEX idx_events_service_status ON market_events(service_type, status);
CREATE INDEX idx_events_provider_time ON market_events(provider_id, created_at);
CREATE INDEX idx_inference_service_version ON inference_states(service_type, model_version);
CREATE INDEX idx_dlq_status ON dead_letter_queue(status, created_at);
```

---

## API Surface

### Ingestion

`POST /api/v1/events/ingest`
- Accepts raw pricing event payload
- Pydantic V2 strict validation with `@field_validator(mode="before")` for currency coercion (e.g., `"$1,250.00"` → `1250.0`, `"Free"` → `0.0`)
- Idempotency check: duplicate `idempotency_key` returns `409 Conflict`
- Validation failure routes to DLQ with full error trace
- Success triggers async `update_posterior` task via Redis
- Returns: `201 Created` with event ID, or `409 Conflict`, or `202 Accepted` (quarantined to DLQ)

### Inference

`GET /api/v1/inference/{service_type}`
- Returns current posterior summary: expected price, 95% HDI, observation count, last update timestamp
- Includes diagnostics snapshot: R-hat, ESS, divergence count

`GET /api/v1/compare/{service_type}`
- Returns Bayesian posterior AND rules-based percentiles side-by-side
- Highlights divergence magnitude and direction
- This endpoint directly demonstrates the rules→Bayesian transition the role requires

### Diagnostics

`GET /api/v1/diagnostics/{service_type}`
- Full model health report: R-hat per parameter, bulk/tail ESS, divergence count and percentage, prior predictive check summary, posterior predictive p-values
- Returns `"healthy"`, `"warning"`, or `"unhealthy"` status with specific failure reasons
- This is the "I know when my model is lying" signal

### Counterfactual Simulation

`POST /api/v1/simulate/counterfactual`
```json
{
  "service_type": "MRI",
  "scenario": "restrict_high_risk",
  "parameters": {
    "exclude_risk_levels": ["high"],
    "price_adjustment_pct": 0.10,
    "supply_shock_factor": 0.8
  },
  "n_simulations": 2000
}
```
- Modifies the data/prior assumptions per scenario definition
- Runs full posterior simulation under modified conditions
- Returns: baseline HDI, counterfactual HDI, delta distribution, revenue impact estimate with credible intervals
- NOT a toy multiply-by-factor approach — actually re-runs inference under structurally different assumptions

### Dead Letter Queue

`GET /api/v1/dlq` — paginated list of quarantined events, filterable by error type and status

`POST /api/v1/dlq/{id}/replay` — re-attempt ingestion of a quarantined event (after schema updates or manual review)

`POST /api/v1/dlq/batch-replay` — replay all pending DLQ events matching a filter

### Data Generator (Development/Demo)

`POST /api/v1/dev/generate`
```json
{
  "n_events": 5000,
  "missingness_rate": 0.15,
  "censoring_rate": 0.08,
  "selection_bias_strength": "moderate",
  "simpsons_paradox": true,
  "service_types": ["MRI", "blood_panel", "consultation"]
}
```
- Generates synthetic healthcare pricing data with configurable pathologies
- Used for demos, testing, and interview walkthroughs
- This module is a feature, not scaffolding

---

## Bayesian Models (Core)

### Model 1: Hierarchical Pricing Model

The primary model. Estimates true market price per service type while accounting for provider-level and region-level heterogeneity.

```
# Pseudocode structure — not implementation
with pm.Model():
    # Hyperpriors (population level)
    mu_global      = Normal(prior from public CMS data)
    sigma_global   = HalfNormal()

    # Provider random effects
    mu_provider    = Normal(mu_global, sigma_provider, shape=n_providers)

    # Region random effects
    mu_region      = Normal(0, sigma_region, shape=n_regions)

    # Observation model
    price_obs      = Normal(mu_provider[provider_idx] + mu_region[region_idx],
                            sigma_obs, observed=prices)
```

Key details:
- Priors informed by public CMS/healthcare pricing benchmarks (documented in `priors/` directory)
- Handles cold start: wide priors with explicit uncertainty communication when n < 10
- Partial pooling across providers prevents overfitting to small-sample providers
- Missing data handled via prior predictive imputation, not mean imputation

### Model 2: Insurance Risk Estimator (Bayesian GLM)

Estimates claim probability and severity by patient profile.

```
# Pseudocode structure
with pm.Model():
    # Patient features (age, risk category, insurance type)
    beta = Normal(0, 1, shape=n_features)

    # Claim probability (logistic)
    p_claim = pm.math.sigmoid(X @ beta)
    claim_occurred = Bernoulli(p_claim, observed=claims)

    # Claim severity (conditional on claim occurring)
    severity = Gamma(alpha, beta, observed=severities[claims==1])
```

Key details:
- Two-part model: probability of claim × severity given claim
- Handles censored claims (patient left network before resolution) via likelihood adjustment
- Outputs: risk score with credible interval per patient profile

### Model 3: Supply-Demand Elasticity

Replaces the matching engine with tighter marketplace logic. Estimates how price changes affect utilization.

```
# Pseudocode structure
with pm.Model():
    # Elasticity parameter (how sensitive demand is to price)
    elasticity = Normal(-0.5, 0.3)  # prior: demand decreases with price

    # Log-linear demand model
    log_demand = alpha + elasticity * log_price + region_effects

    demand_obs = Poisson(exp(log_demand), observed=utilization_counts)
```

Key details:
- Connects pricing decisions to volume outcomes — this is marketplace intuition
- Directly feeds counterfactual simulations ("if we raise MRI prices 10%, how does utilization shift?")
- More relevant to the JD than a matching engine and builds naturally on the pricing model

---

## Background Workers (Celery + Redis)

**`update_posterior`** — triggered on new event ingestion
- Pulls recent `market_event` rows for the relevant service type
- Runs MCMC sampling (NUTS, 2000 draws, 4 chains)
- Computes diagnostics (R-hat, ESS, divergences)
- Writes new `inference_state` row (does not overwrite — maintains history)
- Also updates `rules_baseline` percentiles for comparison
- Timeout: 120s, with fallback to variational inference (ADVI) if MCMC fails to converge

**`run_counterfactual`** — triggered by simulation endpoint
- Clones current data pool, applies scenario modifications
- Runs abbreviated MCMC (1000 draws, 2 chains) for faster turnaround
- Returns delta distribution without persisting to inference_state

**`retry_dlq_batch`** — scheduled or manual trigger
- Re-attempts parsing of pending DLQ events
- Moves successful re-parses to `market_events` with status `'replayed'`
- Increments retry_count on continued failures

---

## Synthetic Data Generator

This is a first-class module, not test scaffolding. It demonstrates your understanding of the data pathologies that make healthcare pricing hard.

### Configurable Pathologies

**Missingness (MNAR — Missing Not At Random)**
- Patient age missing more often for uninsured patients (realistic: no intake form)
- Insurance type missing for out-of-network claims
- Configurable rate: 0–40%

**Censored Claims**
- Right-censoring: patient left network before claim resolution
- Interval-censoring: claim amount known to be "between $500 and $2000" but not exact
- Configurable rate: 0–20%

**Selection Bias**
- Healthier patients more likely to use marketplace (they shop around)
- Sicker patients go to ER (not in dataset)
- Creates systematic underestimate of true market cost if not modeled

**Simpson's Paradox**
- Aggregate trend shows Price↑ → Outcomes↑ (looks good)
- Stratified by provider: Price↑ → Outcomes↓ for every provider
- Caused by high-quality providers charging more AND treating harder cases
- Toggle on/off for demo purposes

### Output Format
- Generates `market_event`-shaped payloads ready for the `/ingest` endpoint
- Includes intentionally messy strings: `"$1,250"`, `"~800"`, `"Free consultation"`, `"N/A"`, `""`
- Saves generation config alongside data for reproducibility

---

## React Dashboard

Two pages. Clean, functional, not flashy. Consumes the FastAPI endpoints.

### Page 1: Marketplace Intelligence

- **Price Overview Table:** Service type, current expected price, 95% HDI, observation count, model health status (green/yellow/red from diagnostics endpoint)
- **Bayesian vs. Rules Comparison:** Per-service chart showing posterior distribution overlaid with rules-based percentile markers (from `/compare` endpoint)
- **Counterfactual Simulator:** Input panel with scenario parameters (service type, price adjustment, supply shock, risk exclusions) → submit → display baseline vs. counterfactual HDI with revenue delta and credible interval
- **Elasticity Curves:** Interactive Plotly chart showing estimated demand response to price changes with uncertainty bands

### Page 2: Operations Console

- **DLQ Browser:** Paginated table of quarantined events with error type, raw payload preview, retry count, status
- **Replay Controls:** Single-event replay button + batch replay with filters
- **Model Diagnostics Panel:** Per-service-type R-hat, ESS, divergence count, prior predictive check results, last update timestamp
- **Ingestion Activity Feed:** Recent events with success/quarantine status

---

## Repo Structure

```
bayesian-health-marketplace/
├── api/
│   ├── main.py                  # FastAPI app, router registration
│   ├── routes/
│   │   ├── ingest.py            # POST /events/ingest
│   │   ├── inference.py         # GET /inference, GET /compare
│   │   ├── diagnostics.py       # GET /diagnostics
│   │   ├── simulate.py          # POST /simulate/counterfactual
│   │   ├── dlq.py               # GET /dlq, POST /dlq/replay
│   │   └── dev.py               # POST /dev/generate (data generator)
│   ├── schemas.py               # Pydantic V2 models with validators
│   ├── dependencies.py          # DB sessions, Redis connections
│   └── middleware.py            # Request logging, error handling
├── models/
│   ├── database.py              # SQLAlchemy table definitions
│   ├── pricing.py               # Hierarchical pricing model (PyMC)
│   ├── insurance_risk.py        # Bayesian GLM for claims (PyMC)
│   ├── elasticity.py            # Supply-demand elasticity model (PyMC)
│   └── rules_engine.py         # Percentile-based baseline for comparison
├── workers/
│   ├── celery_app.py            # Celery configuration
│   ├── update_posterior.py      # MCMC sampling task
│   ├── run_counterfactual.py    # Simulation task
│   └── retry_dlq.py            # DLQ batch retry task
├── data/
│   ├── generator.py             # Synthetic data generator (first-class module)
│   ├── pathologies.py           # Missingness, censoring, selection bias, Simpson's
│   ├── cms_priors.json          # Public CMS benchmarks for prior calibration
│   └── fixtures/                # Static test datasets
├── diagnostics/
│   ├── checks.py                # R-hat, ESS, divergence, PPC evaluators
│   └── reporter.py             # Aggregates checks into health status
├── priors/
│   ├── README.md                # Documents prior choices and justifications
│   └── calibration.py          # Prior predictive checking utilities
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── MarketIntelligence.jsx
│   │   │   └── OpsConsole.jsx
│   │   └── components/
│   │       ├── PriceTable.jsx
│   │       ├── BayesVsRulesChart.jsx
│   │       ├── CounterfactualPanel.jsx
│   │       ├── ElasticityCurve.jsx
│   │       ├── DLQBrowser.jsx
│   │       └── DiagnosticsPanel.jsx
│   └── package.json
├── tests/
│   ├── test_ingest.py           # Messy string coercion, idempotency, DLQ routing
│   ├── test_models.py           # Posterior convergence, prior predictive checks
│   ├── test_diagnostics.py      # Health status logic
│   ├── test_counterfactual.py   # Scenario simulation correctness
│   ├── test_generator.py        # Data pathology verification
│   └── test_comparison.py       # Rules vs Bayesian divergence detection
├── deployment/
│   ├── Dockerfile
│   ├── docker-compose.yml       # API + Postgres + Redis + Celery worker
│   └── railway.toml             # One-click deploy config
├── docs/
│   ├── ARCHITECTURE.md          # System diagram + data flow
│   ├── PRIORS.md                # Prior justification document (interview prep)
│   ├── COUNTERFACTUALS.md       # Methodology for scenario simulation
│   └── INTERVIEW_WALKTHROUGH.md # Talking points per module
└── README.md                    # Overview, quickstart, demo instructions
```

---

## Build Schedule (6 Weeks)

### Weeks 1–2: Ingestion Pipeline + Data Generator

**Deliverables:**
- Postgres schema with all tables and indexes
- Pydantic V2 schemas with currency coercion validators
- `POST /ingest` endpoint with idempotency + DLQ routing
- Redis + Celery skeleton (task dispatch, no model logic yet)
- Synthetic data generator with all four pathology knobs
- Test suite: messy string handling, duplicate rejection, DLQ routing, generator output validation

**Definition of done:** You can POST 5,000 synthetic events with 15% missingness and 8% censoring, see clean events in `market_events`, messy ones in `dead_letter_queue`, and replay quarantined events successfully.

### Weeks 3–4: Bayesian Models + Diagnostics

**Deliverables:**
- Hierarchical pricing model (PyMC) with provider/region random effects
- Insurance risk GLM (two-part: claim probability + severity)
- Rules-based baseline engine (percentile calculations)
- `update_posterior` Celery task with MCMC sampling + ADVI fallback
- Diagnostics module: R-hat, ESS, divergence checks, PPC
- API endpoints: `GET /inference`, `GET /compare`, `GET /diagnostics`
- Test suite: convergence on known synthetic data, cold start behavior, diagnostics thresholds

**Definition of done:** After ingesting synthetic data, `GET /inference/MRI` returns a posterior summary with HDI, `GET /compare/MRI` shows Bayesian vs rules side-by-side, and `GET /diagnostics/MRI` returns a green health status with all checks passing.

### Weeks 5–6: Counterfactuals + Elasticity + Dashboard

**Deliverables:**
- Supply-demand elasticity model
- Counterfactual simulation engine (full posterior re-simulation under modified assumptions)
- `POST /simulate/counterfactual` endpoint
- React dashboard: both pages functional, consuming all API endpoints
- Plotly charts: posterior distributions, Bayesian vs rules overlay, elasticity curves, counterfactual deltas
- Docker Compose: full stack runs with one command
- Deploy to Railway/Fly.io

**Definition of done:** You can open the dashboard, see live price intelligence with health indicators, run a counterfactual ("restrict high-risk patients from MRI") and see the revenue impact distribution update in real time, browse the DLQ and replay events, and view model diagnostics — all from a deployed URL you can share in interviews.

---

## Interview Walkthrough Prep

Each module maps to a specific interview question category:

| They Ask | You Walk Through |
|---|---|
| "How do you handle messy data?" | Data generator pathologies + Pydantic validators + DLQ architecture |
| "Why Bayesian over frequentist?" | Hierarchical model with partial pooling, cold start handling, credible intervals vs confidence intervals |
| "How do you know your model works?" | Diagnostics API: R-hat, ESS, divergences, PPC — live in production, not just notebooks |
| "How would you transition from rules to statistical models?" | `/compare` endpoint showing side-by-side divergence, rules baseline as fallback |
| "Walk me through a counterfactual" | Full posterior simulation methodology, not sensitivity analysis — show the delta distribution |
| "How does this handle scale?" | Async MCMC via Celery, ADVI fallback, idempotent ingestion, indexed queries |
| "What would you build next?" | Causal inference layer (instrumental variables for insurance network effects), online learning (sequential Bayesian updates instead of batch) |

---

## What This Project Is Not

- **Not a notebook.** Every model is behind an API endpoint with typed inputs and structured outputs.
- **Not a tutorial.** The synthetic data generator creates genuinely hard statistical problems. The models handle them.
- **Not a matching engine.** Matching is a different problem. This focuses on pricing, risk, and elasticity — the core marketplace quant surface.
- **Not using LLMs for explanation.** A well-labeled chart with credible intervals communicates better than generated text. The dashboard speaks for itself.
- **Not Streamlit.** The React frontend signals production ownership, not prototyping.

---

## Current Status: READY TO START — WEEK 1