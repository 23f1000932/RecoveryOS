# RecoveryOS — techstack.md

## 1. Purpose

This document is the **technology-stack lock** for RecoveryOS.

The coding agent must treat this file as the authoritative technology decision record.

The primary goal is to prevent technology drift, unnecessary complexity, and replacement of the agreed stack with unrelated frameworks or infrastructure.

Do not introduce a new framework, database, UI library, orchestration platform, message broker, vector database, or cloud service unless explicitly approved.

---

# 2. STACK AT A GLANCE

| Layer | REQUIRED TECHNOLOGY |
|---|---|
| Frontend | React |
| Frontend build tool | Vite |
| Frontend styling | Tailwind CSS |
| Charts | Recharts |
| Frontend language | TypeScript |
| Backend | Python |
| Backend API | FastAPI |
| Backend validation | Pydantic |
| Database | Supabase PostgreSQL |
| ORM/data access | Supabase/PostgreSQL repositories |
| ML | Python + pandas + scikit-learn + XGBoost |
| LLM | Gemini API |
| Payment integration | Razorpay Test Mode |
| Simulation | Python |
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Database hosting | Supabase |
| Version control | Git + GitHub |
| API style | REST/JSON |
| Configuration | Environment variables |
| Testing | pytest + frontend test tooling appropriate to React/Vite |
| Primary serialization | JSON |
| Policy configuration | YAML |

---

# 3. NON-NEGOTIABLE STACK RULE

The project is intentionally a **simple modular monolith**.

Architecture:

```text
React/Vite frontend
        ↓ REST/JSON
FastAPI backend
        ↓
Supabase PostgreSQL
```

ML, Gemini, simulation, and Razorpay are backend integrations/modules.

Do NOT turn this into:

```text
microservices
Kubernetes
Kafka
Redis
event bus
serverless function mesh
multi-agent framework
vector database
```

unless explicitly requested later.

---

# 4. FRONTEND

## Required

```text
React
Vite
TypeScript
Tailwind CSS
Recharts
```

## Why

### React

Used for:
- dashboard;
- recovery queue;
- case detail;
- simulator;
- policy UI;
- audit timeline.

### Vite

Used as the frontend build tool.

Do not migrate to Next.js unless explicitly instructed.

### TypeScript

Required for frontend code.

Use typed:
- API responses;
- component props;
- domain models;
- state;
- chart data.

Avoid `any`.

### Tailwind CSS

Primary styling system.

Use centralized CSS variables for design tokens.

Do not add another CSS framework.

### Recharts

Required charting library.

Do not add Chart.js, D3, ECharts, or another chart framework unless explicitly requested.

---

# 5. FRONTEND API CLIENT

Use a small typed API layer.

Recommended:

```text
frontend/src/services/api.ts
```

Example structure:

```text
api/
├── dashboard.ts
├── recoveryCases.ts
├── simulator.ts
├── policies.ts
└── audit.ts
```

Do not scatter raw `fetch()` calls throughout components.

Components should call typed service functions.

---

# 6. FRONTEND STATE MANAGEMENT

Start with:

- React state;
- React context only where genuinely useful;
- server data fetched through the API layer.

Do NOT introduce Redux, Zustand, MobX, or another global state library unless actual application complexity requires it and approval is given.

The application is not large enough to justify heavy state infrastructure by default.

---

# 7. BACKEND

## Required

```text
Python
FastAPI
Pydantic
```

### FastAPI responsibilities

FastAPI is responsible for:
- REST endpoints;
- request validation;
- response schemas;
- webhook endpoints;
- dependency injection;
- error handling.

### Pydantic responsibilities

Use Pydantic for:
- request models;
- response models;
- domain DTOs;
- configuration validation;
- structured agent outputs where appropriate.

---

# 8. PYTHON VERSION

Use a currently supported stable Python version compatible with the selected libraries.

Recommended:

```text
Python 3.12
```

Do not use an obsolete Python version.

---

# 9. DATABASE

## Required

**Supabase PostgreSQL**

Supabase provides:
- PostgreSQL;
- database hosting;
- SQL interface;
- optional authentication/storage if later required.

The core application must use PostgreSQL semantics.

Do not migrate to:
- MongoDB;
- Firebase;
- SQLite for production;
- DynamoDB;
- MySQL.

SQLite may be used only for isolated local tests if absolutely necessary, but production schema and behavior must target PostgreSQL.

---

# 10. DATABASE ACCESS

Use a repository/data-access layer.

Recommended:

```text
backend/db/
├── schema.sql
└── repositories/
    ├── payments.py
    ├── customers.py
    ├── recovery_cases.py
    ├── actions.py
    ├── audit.py
    └── experiments.py
```

Business logic must not contain random SQL strings throughout the codebase.

Keep database access separate from:
- optimizer;
- ML;
- agent;
- UI.

---

# 11. CORE BACKEND MODULES

Required modules:

```text
backend/
├── api/
├── orchestrator/
├── domain/
├── optimizer/
├── guardrails/
├── agents/
├── tools/
├── services/
├── webhooks/
└── db/
```

Responsibilities:

### `domain/`

Shared business models and enums.

### `orchestrator/`

Controls the recovery workflow.

### `optimizer/`

Calculates expected financial value and ranks actions.

### `guardrails/`

Applies deterministic merchant policy.

### `agents/`

Gemini integration and explanation.

### `tools/`

Controlled action adapters.

### `services/`

External/internal data access.

### `webhooks/`

Razorpay webhook processing.

### `db/`

Persistence.

---

# 12. ML STACK

Required:

```text
Python
pandas
scikit-learn
XGBoost
```

## Development order

First implement:

```text
RuleBasedRecoveryModel
```

Then:

```text
XGBoostRecoveryModel
```

Both must implement the same interface.

Example:

```python
class RecoveryOutcomeModel(Protocol):
    def predict_action_outcomes(
        self,
        case_context: CaseContext,
        actions: list[str],
    ) -> list[ActionPrediction]:
        ...
```

The optimizer must not care which implementation is active.

---

# 13. ML RESPONSIBILITY

ML predicts outcome probabilities.

ML does NOT:
- execute payments;
- enforce budgets;
- approve actions;
- decide whether an action is legally/operationally permitted;
- calculate authoritative accounting totals.

Correct architecture:

```text
ML
 ↓
probabilities
 ↓
Expected-value optimizer
 ↓
Guardrails
 ↓
Approval
 ↓
Execution
```

---

# 14. SYNTHETIC DATA

Use Python for data generation.

Required capabilities:
- fixed random seed;
- realistic customer/payment distributions;
- failure reasons;
- action-dependent latent outcomes;
- reproducible experiments.

Recommended libraries:

```text
numpy
pandas
scikit-learn
```

`numpy` may be used for numerical simulation.

---

# 15. SIMULATOR

The simulator is Python-based.

It must use the same domain concepts as the live recovery system.

Architecture:

```text
Synthetic Dataset
      ↓
Baseline Policy ──────────┐
                          ├──→ Same experiment environment
RecoveryOS Policy ────────┘
      ↓
Business Metrics
```

Do not build the simulator as a separate fake frontend-only system.

---

# 16. BASELINE

Baseline is deterministic:

```text
failed payment
→ immediate retry once
→ success = recovered
→ failure = stop
```

No Gemini.
No ML.
No dynamic optimization.

---

# 17. OPTIMIZATION TECHNOLOGY

No optimization framework is required.

Use plain Python deterministic calculations.

Core formula:

```text
expected_gross_recovery
=
probability × recoverable_amount
```

Then:

```text
expected_net_revenue
=
expected_gross_recovery
-
intervention_cost
-
incentive_cost
-
contact_cost
```

Do not use an LLM to calculate these values.

Do not add a mathematical optimization solver unless future requirements actually require one.

---

# 18. GEMINI

## Required LLM

**Gemini API**

Use it for:
- contextual reasoning;
- decision explanation;
- structured recommendation where appropriate;
- human-readable summaries.

Do not make Gemini the financial source of truth.

---

# 19. GEMINI BOUNDARY

Gemini can receive:

```text
case context
candidate predictions
expected values
guardrail results
policy context
```

Gemini can produce:

```text
explanation
summary
structured reasoning
```

Gemini cannot directly:
- retry a payment;
- issue an incentive;
- send a recovery message;
- approve itself;
- bypass guardrails;
- modify financial calculations.

Backend code validates everything.

---

# 20. RAG

RAG is **optional**.

Do not introduce a vector database just because the project mentions RAG/AI.

If RAG is implemented later, its only initial purpose should be retrieving merchant policy/context such as:
- recovery policy;
- incentive rules;
- escalation rules;
- operating guidelines.

The authoritative policy remains structured YAML/database configuration.

RAG cannot override deterministic guardrails.

If the feature does not materially improve the demo, leave it out of the MVP.

---

# 21. RAZORPAY

Use:

**Razorpay Test Mode**

Integration responsibilities:
- payment context;
- failed-payment webhook;
- webhook signature validation;
- event idempotency;
- payment-state verification.

Do not use production payment credentials.

Do not expose Razorpay secret keys in React.

---

# 22. WEBHOOK TECHNOLOGY

Webhook endpoint:

```text
POST /webhooks/razorpay
```

FastAPI receives the request.

Processing:

```text
HTTP request
↓
signature validation
↓
event deduplication
↓
event persistence
↓
payment normalization
↓
RecoveryPipeline
```

Do not put the recovery decision logic directly inside the webhook route.

---

# 23. HOSTING

## Frontend

**Vercel**

Deploy React/Vite frontend.

## Backend

**Render**

Deploy FastAPI backend.

## Database

**Supabase**

Host PostgreSQL.

## LLM

Gemini API.

## Payments

Razorpay Test Mode.

Architecture:

```text
Browser
   ↓
Vercel
React/Vite
   ↓ HTTPS REST
Render
FastAPI
   ├── Supabase PostgreSQL
   ├── Gemini API
   └── Razorpay Test Mode
```

---

# 24. LOCAL DEVELOPMENT

Recommended:

```text
frontend/
npm install
npm run dev
```

Backend:

```text
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Windows activation may use the appropriate PowerShell/Command Prompt syntax.

---

# 25. DEPENDENCY POLICY

Keep dependencies minimal.

## Frontend core

Expected:

```text
react
react-dom
vite
typescript
tailwindcss
recharts
```

Additional small utilities are acceptable when justified.

## Backend core

Expected:

```text
fastapi
uvicorn
pydantic
python-dotenv
```

## ML

Expected:

```text
numpy
pandas
scikit-learn
xgboost
```

## Integrations

Use the official or appropriate SDK/client for:
- Gemini;
- Razorpay;
- Supabase/PostgreSQL.

Do not add libraries merely because they are popular.

---

# 26. TESTING STACK

## Backend

Use:

```text
pytest
```

Test:
- optimizer;
- guardrails;
- state transitions;
- idempotency;
- simulator;
- API endpoints;
- financial formulas.

## Frontend

Use the existing React/Vite-compatible testing approach selected during implementation.

Prioritize tests for:
- critical user flows;
- approval states;
- blocked execution;
- dashboard metric rendering;
- API error handling.

Do not add an oversized testing framework stack.

---

# 27. CONFIGURATION

Use environment variables.

Required:

```text
DATABASE_URL=
GEMINI_API_KEY=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
VITE_API_BASE_URL=
```

Optional:

```text
MODEL_PATH=
LOG_LEVEL=INFO
ENVIRONMENT=development
```

Never commit secrets.

---

# 28. POLICY CONFIGURATION

Merchant recovery policy should be represented as structured configuration.

Recommended:

```text
policies/recovery_policy.yaml
```

Example:

```yaml
version: "1.0"

max_retries_per_customer: 2
max_messages_per_customer: 2
max_incentive_per_customer: 100
daily_incentive_pool: 5000

high_value_threshold: 10000
recovery_window_hours: 48

min_expected_net_revenue: 100
min_model_confidence: 0.65
auto_action_probability: 0.70
```

The policy loader validates this configuration.

---

# 29. DATA CONTRACTS

Frontend and backend communicate through typed JSON REST contracts.

Do not return arbitrary Python objects.

Use Pydantic response models.

Frontend TypeScript types should correspond to backend response contracts.

When a contract changes:
1. update backend schema;
2. update frontend type;
3. update API client;
4. update tests.

---

# 30. API STYLE

Use REST.

Examples:

```text
GET  /health
GET  /api/dashboard/summary

GET  /api/recovery-cases
GET  /api/recovery-cases/{case_id}

POST /api/recovery-cases/{case_id}/analyze
POST /api/recovery-cases/{case_id}/approve
POST /api/recovery-cases/{case_id}/reject
POST /api/recovery-cases/{case_id}/execute
POST /api/recovery-cases/{case_id}/stop

GET  /api/recovery-cases/{case_id}/audit

POST /api/simulator/run
GET  /api/simulator/{experiment_id}

POST /webhooks/razorpay
```

Do not introduce GraphQL.

---

# 31. LOGGING

Use Python logging.

Log:
- request IDs where practical;
- case IDs;
- action IDs;
- state transitions;
- integration errors;
- model version;
- policy version.

Never log:
- secrets;
- API keys;
- unnecessary sensitive payment/customer data.

---

# 32. ERROR HANDLING

Backend errors use a consistent structure:

```json
{
  "error": {
    "code": "CASE_NOT_EXECUTABLE",
    "message": "Case is waiting for approval.",
    "details": {}
  }
}
```

Do not return stack traces to the frontend.

Frontend should render useful user-facing messages.

---

# 33. SECURITY TECHNOLOGY RULES

Required:
- HTTPS in deployed environments;
- server-side secrets;
- webhook signature validation;
- idempotency;
- backend authorization of execution;
- server-side financial calculations.

Never trust:
- frontend-selected action;
- frontend-provided expected revenue;
- frontend-provided guardrail result;
- unsigned webhook data.

---

# 34. ARCHITECTURAL SIMPLICITY

Do not introduce infrastructure for theoretical scale.

For this project:

```text
React
+
FastAPI
+
PostgreSQL
+
Python ML
+
Gemini
+
Razorpay Test Mode
```

is enough.

A clean modular monolith is preferred over a complicated distributed system.

---

# 35. TECHNOLOGIES EXPLICITLY NOT APPROVED BY DEFAULT

Do not introduce:

- Next.js
- Vue
- Angular
- Svelte
- Bootstrap
- Material UI
- Chakra UI
- Ant Design
- shadcn/ui as a replacement design system
- Redux
- Zustand
- MongoDB
- Firebase
- DynamoDB
- MySQL
- Kafka
- RabbitMQ
- Redis
- Kubernetes
- Docker Swarm
- Terraform
- LangChain
- LangGraph
- AutoGen
- CrewAI
- Pinecone
- Weaviate
- Milvus
- Elasticsearch
- GraphQL
- Celery
- Airflow
- separate microservices
- another chart library

Some may be valid in a different project, but they are not part of the RecoveryOS baseline stack.

If a new dependency is proposed, first ask:

> “Does the current stack genuinely fail to solve this requirement?”

If no, do not add it.

---

# 36. IMPLEMENTATION ORDER

The coding agent should implement technologies in this order:

### 1. Frontend shell

React + Vite + TypeScript + Tailwind.

### 2. Backend shell

FastAPI + Pydantic.

### 3. Database

Supabase PostgreSQL.

### 4. Domain models

Shared business contracts.

### 5. Simulator

Python + pandas/numpy.

### 6. Baseline

Deterministic recovery policy.

### 7. ML

scikit-learn + XGBoost.

### 8. Optimizer

Pure Python deterministic expected-value calculations.

### 9. Guardrails

Pure Python policy engine.

### 10. RecoveryPipeline

Connect the complete decision flow.

### 11. Controlled execution adapters

Simulation first.

### 12. Gemini

Add explanation/reasoning after deterministic flow works.

### 13. Dashboard

React + Recharts.

### 14. Razorpay

Test Mode webhook + verification.

### 15. Deployment

Vercel + Render + Supabase.

---

# 37. TECHNOLOGY OWNERSHIP

| Responsibility | Technology |
|---|---|
| UI | React |
| Build | Vite |
| Styling | Tailwind CSS |
| Typography | Google Fonts / Playfair Display + Source Sans 3 + IBM Plex Mono |
| Charts | Recharts |
| API | FastAPI |
| Validation | Pydantic |
| Business logic | Python |
| ML | XGBoost |
| Data processing | pandas/numpy |
| Database | PostgreSQL via Supabase |
| LLM | Gemini API |
| Payment gateway | Razorpay Test Mode |
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Database hosting | Supabase |
| Testing | pytest + React-compatible frontend tests |
| Policy | YAML |
| Configuration | environment variables |

---

# 38. FINAL TECH-STACK LOCK

The canonical RecoveryOS stack is:

```text
FRONTEND
React
Vite
TypeScript
Tailwind CSS
Recharts

BACKEND
Python
FastAPI
Pydantic

DATABASE
Supabase PostgreSQL

ML
pandas
numpy
scikit-learn
XGBoost

AI
Gemini API

PAYMENTS
Razorpay Test Mode

HOSTING
Vercel
Render
Supabase

TESTING
pytest
React/Vite-compatible frontend testing

CONFIG
YAML + environment variables
```

The coding agent must preserve this stack unless the user explicitly changes it.

---

# 39. RELATION TO ARCHITECTURE

`architecture.md` answers:

> **How should RecoveryOS work?**

`techstack.md` answers:

> **Which technologies must RecoveryOS use?**

`design.md` answers:

> **How should RecoveryOS look and feel?**

All three files are complementary.

If there is ambiguity:

```text
architecture.md
→ system behavior

techstack.md
→ technology choice

design.md
→ visual/UX choice
```

Do not use one document to silently override another.

---

# 40. FINAL CODING-AGENT INSTRUCTION

Build RecoveryOS as a clean, maintainable, deployable modular monolith using the locked stack above.

Do not optimize for the number of technologies used.

Optimize for:

```text
clarity
+
correctness
+
reproducibility
+
safe execution
+
measurable revenue recovery
+
excellent UX
```

The project should be impressive because the system is intelligently designed—not because the repository contains unnecessary infrastructure.
