# RecoveryOS

> **AI-powered payment recovery orchestrator for Razorpay — Buildathon 2025**

RecoveryOS is a production-ready backend + dashboard that intercepts failed Razorpay payments, runs them through an ML-optimized 10-stage recovery pipeline, and presents merchants with explainable, auditable decisions — all without ever touching financial values in the AI layer.

---

## The Business Question

> _"A customer's payment failed. What should we do about it — and how much will we actually recover?"_

RecoveryOS answers this by:
1. **Predicting** the probability each recovery action succeeds (XGBoost, 6 models)
2. **Optimizing** for Expected Net Revenue — not just recovery rate
3. **Enforcing guardrails** — no retry after the limit, no incentive without budget, no action on already-recovered payments
4. **Routing high-value cases** to human approval before any money moves
5. **Measuring the lift** — Baseline (naive retry) vs AI in the same experiment batch

---

## The Recovery Loop

```
Razorpay Webhook / Dashboard
         │
         ▼
   ┌─────────────┐
   │  DETECT     │  validate case_id and context
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  PREDICT    │  XGBoost (6 models) → P(success | action)
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  OPTIMIZE   │  ENR = P × Amount − costs  →  rank actions
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  GUARD      │  retry limit · budget · expiry · approval gate
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  APPROVE    │  human approval for high-value cases
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  EXPLAIN    │  Gemini 2.5 Flash: structured, auditable explanation
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  EXECUTE    │  action adapter (retry / reminder / incentive / escalate)
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  VERIFY     │  confirm payment recovered via Razorpay API
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  AUDIT      │  every event logged with input + output snapshot
   └─────────────┘
```

**Rule**: LLM proposes explanations. Deterministic code enforces financial decisions.

---

## Architecture

| Component | Technology |
|---|---|
| API & Pipeline | FastAPI + asyncpg |
| ML Models | XGBoost (6 per-action classifiers) |
| AI Explanation | Gemini 2.5 Flash (read-only, no execution) |
| Database | Supabase PostgreSQL |
| Payments | Razorpay (webhook + signature validation) |
| Frontend | React + TypeScript + Recharts |
| Deployment | Render (backend) + Vercel (frontend) |
| Simulations | Same RecoveryPipeline, different seed |
| Tests | pytest (130 tests, 0 DB required) |

---

## Live Demo

| Service | URL |
|---|---|
| Frontend (Vercel) | _(set after deployment)_ |
| Backend API (Render) | _(set after deployment)_ |
| API Docs (Swagger) | `<backend-url>/docs` |
| Health | `<backend-url>/health` |

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/23f1000932/RecoveryOS.git
cd RecoveryOS
```

### 2. Backend

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env            # fill in credentials (see Environment Variables below)

# Start server
uvicorn backend.main:app --reload
```

API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`

### 3. Database

Apply the schema once via Supabase SQL Editor:

```sql
-- Run the contents of backend/db/schema.sql in your Supabase project
```

Optionally seed the 5 demo cases (Cases A–E from architecture §36):

```bash
.venv\Scripts\python scripts/seed_demo_data.py
```

### 4. Train ML Models

Pre-trained artifacts are in `ml/models/` (git-ignored by default — re-run to regenerate):

```bash
.venv\Scripts\python -m ml.train --rows 50000 --seed 42
# Trains 6 XGBoost models, saves to ml/models/, writes ml/models/evaluation_report.json
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Supabase PostgreSQL URL (`postgresql+asyncpg://...`) |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key (for AI explanations) |
| `RAZORPAY_KEY_ID` | ✅ | Razorpay Test Mode Key ID |
| `RAZORPAY_KEY_SECRET` | ✅ | Razorpay Test Mode Key Secret |
| `RAZORPAY_WEBHOOK_SECRET` | ✅ | Razorpay webhook signing secret |
| `VITE_API_BASE_URL` | ✅ | Backend URL used by React frontend |
| `MODEL_PATH` | ☐ | Path to XGBoost model directory (defaults to `ml/models/`) |
| `LOG_LEVEL` | ☐ | `DEBUG` / `INFO` / `WARNING` (default: `INFO`) |
| `ENVIRONMENT` | ☐ | `development` / `production` (default: `development`) |

> **Security**: `RAZORPAY_WEBHOOK_SECRET` is used for HMAC-SHA256 signature validation on every incoming webhook. If not set, the backend logs a warning and accepts all events (development only).

---

## Running Tests

```bash
# Unit tests (no DB, no external APIs) — 113 tests
.venv\Scripts\python -m pytest tests/unit/ -v

# Pipeline end-to-end integration tests (no DB, no Gemini) — 9 tests
.venv\Scripts\python -m pytest tests/integration/test_pipeline_e2e.py -v

# Simulator reproducibility tests — 8 tests
.venv\Scripts\python -m pytest tests/simulator/ -v

# Full suite (skips Gemini API tests if GEMINI_API_KEY not set)
.venv\Scripts\python -m pytest tests/ -q --ignore=tests/integration/test_agent_integration.py --ignore=tests/integration/test_training_pipeline.py

# Gemini integration tests (requires GEMINI_API_KEY)
.venv\Scripts\python -m pytest tests/integration/test_agent_integration.py -v
```

**Current results**: 130 tests, 0 failures, 5 deprecation warnings (FastAPI lifecycle events — non-breaking).

---

## Running the Simulator

The simulator runs A/B experiments comparing Baseline (naive retry-now) vs RecoveryOS AI on the same synthetic batch.

**Via API:**
```bash
# Trigger an experiment
curl -X POST http://localhost:8000/api/simulator/run \
  -H "Content-Type: application/json" \
  -d '{"rows": 1000, "seed": 42}'
# Returns: {"experiment_id": "..."}

# Poll for results
curl http://localhost:8000/api/simulator/experiments/{experiment_id}
```

**Via Dashboard:** Navigate to the Simulator page, configure rows/seed, click Run.

Results include: baseline recovered, AI recovered, incremental lift, net incremental revenue, action distribution.

---

## Deployment

### Backend → Render

1. Connect your GitHub repo in [Render Dashboard](https://render.com)
2. Select **Web Service** → **Docker** runtime
3. Set environment variables in Render → Environment
4. Deploy — health check runs at `/health`

The `render.yaml` in the repo root automates this configuration.

### Frontend → Vercel

1. Import the repo in [Vercel Dashboard](https://vercel.com)
2. Set **Root Directory** to `frontend/`
3. Add environment variable: `VITE_API_BASE_URL` = your Render backend URL
4. Deploy — `vercel.json` handles SPA routing

### Razorpay Webhook Setup

1. In Razorpay Dashboard → Settings → Webhooks → Add Webhook
2. URL: `https://<your-render-url>/webhooks/razorpay`
3. Events to subscribe: `payment.failed`
4. Copy the signing secret → add as `RAZORPAY_WEBHOOK_SECRET` in Render

---

## Project Structure

```
RecoveryOS/
├── backend/
│   ├── agents/          # Gemini agent (explain-only, no execution)
│   ├── api/             # FastAPI routes (cases, simulator, audit, webhooks)
│   ├── db/              # Supabase repositories + connection pool
│   ├── domain/          # Enums, domain models
│   ├── guardrails/      # Policy enforcement engine
│   ├── ml_models/       # Model protocol, RuleBased, XGBoost wrappers
│   ├── optimizer/       # Expected-value optimizer + cost model
│   ├── orchestrator/    # RecoveryPipeline (10 stages), Baseline, CaseContext
│   └── tools/           # Action adapters (retry, reminder, incentive, escalate)
├── frontend/
│   └── src/
│       ├── components/  # Charts, layout, controls
│       ├── pages/       # CommandCenter, RecoveryQueue, CaseDetail, Simulator, Audit
│       ├── services/    # API client
│       └── types/       # TypeScript domain types
├── ml/
│   ├── generate_data.py # Synthetic dataset generator (reproducible seed)
│   ├── train.py         # XGBoost training CLI
│   ├── evaluate.py      # Per-model evaluation + report
│   └── models/          # Trained artifacts (*.joblib, evaluation_report.json)
├── policies/
│   └── recovery_policy.yaml  # Guardrail thresholds (max_retries, high_value_threshold, …)
├── scripts/
│   └── seed_demo_data.py     # Seeds 5 demo cases (A–E)
├── tests/
│   ├── unit/            # 113 unit tests (no DB, no external APIs)
│   ├── integration/     # Pipeline e2e + Gemini agent tests
│   └── simulator/       # Reproducibility + metric identity tests
├── Dockerfile           # Backend container (Python 3.12-slim)
├── render.yaml          # Render.com deployment config
└── architecture_v2.md   # Full system specification
```

---

## Key Design Decisions

| Rule | Implementation |
|---|---|
| **LLM proposes; code enforces** | Gemini writes explanations. Optimizer + guardrails make financial decisions. |
| **No DB → no crash** | All endpoints degrade gracefully when DB unavailable. |
| **Gemini cannot execute** | Agent only calls `explain_decision()`. No adapter or financial method exposed. |
| **Webhooks always 200** | Razorpay expects `200 OK` — errors are logged, not returned. |
| **Same pipeline everywhere** | Simulator, Dashboard, and Webhook use the identical `RecoveryPipeline`. |
| **Approval gates high-value** | Cases above `high_value_threshold` block at stage 7 until `approved=True`. |

---

## Tech Stack

| Layer | Stack |
|---|---|
| Language | Python 3.12, TypeScript 5 |
| API Framework | FastAPI + Uvicorn |
| Database Driver | asyncpg (async PostgreSQL) |
| ML | XGBoost, scikit-learn, pandas, numpy |
| AI | Google Gemini 2.5 Flash (`google-genai`) |
| Frontend | React 18, Vite, Recharts, CSS Modules |
| Payments | Razorpay (webhooks + HMAC-SHA256 validation) |
| Database | Supabase (managed PostgreSQL) |
| Testing | pytest, pytest-asyncio |
| Deployment | Render (Docker), Vercel (static SPA) |

---

## Architecture Reference

Full specification: [`architecture_v2.md`](./architecture_v2.md) · [`techstack.md`](./techstack.md) · [`design.md`](./design.md)

The architecture document defines: 48 numbered sections covering domain model, pipeline stages, financial formulas, guardrail rules, agent safety constraints, simulator design, webhook processing, API contract, database schema, and the 12-phase build order.
