# RecoveryOS — Architecture Specification v2

## Coding-Agent Master Specification
### Razorpay AI Buildathon — Track 03: AI Revenue Recovery

> **STATUS: AUTHORITATIVE ENGINEERING SPECIFICATION**
>
> This document supersedes the previous `architecture.md`.
> A coding agent must read this entire file before changing or creating project code.
> If an implementation choice is not explicitly specified here, prefer the simplest safe implementation that preserves the architecture and the non-negotiable rules below.

---

## 0. SOURCE, SCOPE, AND DESIGN INTENT

RecoveryOS is a revenue-recovery decision engine for failed payments. Its core loop is:

**Detect → Contextualize → Predict → Optimize → Guard → Approve if needed → Execute → Verify → Measure → Audit**

The MVP scope is **failed-payment recovery**. Do not implement checkout abandonment, subscriptions, mandates, receivables, or other leakage types until this loop is complete and stable.

The system must not become a generic chatbot, generic RAG application, or “AI retries payments” demo.

The project must prove:

> **How much more net revenue can a merchant recover when RecoveryOS intelligently chooses interventions instead of following a fixed retry policy?**

---

# 1. NON-NEGOTIABLE ARCHITECTURE RULES

## Rule 1 — LLM proposes; deterministic code enforces

The LLM may:
- inspect structured context;
- summarize;
- explain;
- recommend among already-computed candidates.

The LLM may NOT:
- directly call a payment API;
- directly issue an incentive;
- change merchant policy;
- bypass guardrails;
- calculate authoritative financial values;
- override approval requirements;
- declare a payment recovered without verification.

Every money-moving or budget-consuming operation must follow:

```text
proposal
→ deterministic validation
→ policy/guardrail check
→ approval check
→ controlled tool
→ verification
→ audit
```

## Rule 2 — Financial numbers are deterministic

Backend code owns:
- transaction amount;
- expected gross recovery;
- expected net revenue;
- intervention cost;
- incentive cost;
- contact cost;
- recovered amount;
- incremental recovery;
- net incremental recovery.

Never let Gemini generate authoritative financial numbers.

## Rule 3 — One pipeline for simulator and live workflow

The simulator, dashboard, and Razorpay webhook must use the same core `RecoveryPipeline`.

```text
Simulator event ───────┐
Dashboard request ─────┼──→ RecoveryPipeline
Razorpay webhook ──────┘
```

Only the event source and execution adapter may differ.

## Rule 4 — Safe failure

If Gemini is unavailable, the deterministic optimizer still works.

If ML is unavailable, use a documented deterministic fallback.

If Razorpay is unavailable, do not claim recovery.

If verification fails, never mark the case recovered.

## Rule 5 — Idempotency everywhere

Duplicate webhook events and duplicate action requests must never cause duplicate financial actions.

## Rule 6 — Explicit state machine

Use a finite state machine. Do not invent arbitrary status strings throughout the code.

## Rule 7 — No unnecessary infrastructure

Do NOT add Kubernetes, Kafka, Redis, microservices, multi-agent frameworks, or a vector database unless a real optional RAG feature requires it.

---

# 2. PRODUCT DEFINITION

## Name

**RecoveryOS — AI Revenue Recovery Orchestrator**

## One-line description

An AI-assisted revenue-recovery system that predicts outcomes of multiple allowed interventions, selects the action with the highest expected net revenue under merchant policy, executes it safely, verifies the result, and proves incremental revenue versus a baseline.

## North-star metric

```text
incremental_recovery
=
AI_recovered_revenue
-
baseline_recovered_revenue

net_incremental_recovery
=
incremental_recovery
-
incremental_intervention_cost
```

## Core differentiation

The system must communicate:

> “We are not building an agent that blindly retries failed payments. We are building an intelligence layer that decides when recovery is worth attempting, which allowed intervention maximizes expected net revenue, and whether the strategy actually created incremental revenue.”

The agent must be able to choose **DO NOTHING**.

---

# 3. CANDIDATE ACTIONS

The fixed MVP candidate set is:

```text
retry_now
retry_later
reminder
incentive
escalate
do_nothing
```

Do not add new actions without documenting:
- prediction behavior;
- cost model;
- guardrail rules;
- simulator behavior;
- tests;
- UI representation.

### Action meanings

`retry_now` — immediate retry through a controlled adapter.

`retry_later` — delayed retry or safe simulated delayed intervention.

`reminder` — recovery reminder.

`incentive` — merchant-approved incentive subject to budgets.

`escalate` — send to human/merchant review.

`do_nothing` — stop because recovery is not economically or operationally justified.

---

# 4. SYSTEM ARCHITECTURE

```text
                         ┌──────────────────────┐
                         │ Razorpay Test Mode   │
                         │ payment.failed       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Webhook Adapter      │
                         │ signature +          │
                         │ idempotency          │
                         └──────────┬───────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    RECOVERY PIPELINE                         │
│                                                             │
│  1. Detect                                                  │
│  2. Contextualize                                           │
│  3. Predict                                                 │
│  4. Optimize                                                │
│  5. Guard                                                   │
│  6. Approval                                                │
│  7. Execute                                                 │
│  8. Verify                                                  │
│  9. Measure                                                 │
│ 10. Audit                                                   │
└─────────────────────────────────────────────────────────────┘
            │              │              │
            ▼              ▼              ▼
       ┌─────────┐    ┌──────────┐   ┌─────────────┐
       │ ML Model│    │ Optimizer│   │ Guardrails  │
       └─────────┘    └──────────┘   │ + Budget    │
                                     └─────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                  ┌────────────────┐
                  │ DecisionProposal│
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Gemini Agent   │
                  │ explanation    │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Approval Gate  │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Action Adapter │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Verification   │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Audit + Metrics│
                  └────────────────┘

Simulator ────────────────┐
Dashboard ────────────────┼──→ SAME RecoveryPipeline
Webhook ──────────────────┘
```

---

# 5. END-TO-END RECOVERY PIPELINE

Implement:

```text
backend/orchestrator/recovery_pipeline.py
```

Recommended public interface:

```python
class RecoveryPipeline:
    def process_case(
        self,
        case_id: str,
        source: str,
        execution_mode: str,
    ) -> RecoveryResult:
        ...
```

`source`:
- `simulator`
- `webhook`
- `dashboard`

`execution_mode`:
- `simulation`
- `test_mode`
- `dry_run`

## Stage 1 — Detect

Input:
- failed payment event or existing recovery case.

Output:
- recovery case ID;
- normalized payment context.

## Stage 2 — Contextualize

Load:
- payment;
- customer;
- historical behavior;
- failure reason;
- attempt count;
- time since failure;
- merchant policy;
- current budget;
- previous recovery actions.

## Stage 3 — Predict

Generate outcome probabilities for every candidate action.

Example:

```json
{
  "retry_now": 0.61,
  "retry_later": 0.79,
  "reminder": 0.52,
  "incentive": 0.87,
  "escalate": 0.40,
  "do_nothing": 0.08
}
```

These are model outputs, not final financial decisions.

## Stage 4 — Optimize

Calculate expected financial value for each action.

## Stage 5 — Guard

Apply deterministic policy and safety checks.

Blocked actions must be removed or marked blocked. If the selected action becomes invalid, re-rank remaining allowed actions.

## Stage 6 — Approval

If approval is required:
- create pending approval state;
- do not execute;
- expose approval UI.

## Stage 7 — Execute

Only an approved action reaches a controlled action adapter.

## Stage 8 — Verify

Check actual payment state.

Never assume:
- retry = success;
- API response = recovered;
- action submitted = revenue recovered.

## Stage 9 — Measure

Calculate:
- actual recovered amount;
- intervention cost;
- incremental recovery;
- net incremental recovery.

## Stage 10 — Audit

Write all meaningful decision and execution events to the audit trail.

---

# 6. STATE MACHINE

Use one strict enum:

```text
CREATED
ANALYZING
DECISION_READY
PENDING_APPROVAL
APPROVED
EXECUTING
VERIFYING
RECOVERED
STOPPED
ESCALATED
FAILED
EXPIRED
UNKNOWN
```

Allowed transitions:

```text
CREATED
  → ANALYZING

ANALYZING
  → DECISION_READY
  → STOPPED
  → ESCALATED
  → FAILED

DECISION_READY
  → PENDING_APPROVAL
  → APPROVED
  → STOPPED
  → ESCALATED

PENDING_APPROVAL
  → APPROVED
  → STOPPED
  → ESCALATED

APPROVED
  → EXECUTING

EXECUTING
  → VERIFYING
  → FAILED

VERIFYING
  → RECOVERED
  → STOPPED
  → FAILED
  → UNKNOWN
```

Terminal states:

```text
RECOVERED
STOPPED
ESCALATED
FAILED
EXPIRED
```

Every transition must be auditable.

---

# 7. DATABASE SCHEMA

Use Supabase PostgreSQL.

## merchants

```text
id UUID PK
name TEXT
retry_limit INT
message_limit INT
max_incentive_per_customer NUMERIC
daily_incentive_pool NUMERIC
high_value_threshold NUMERIC
min_expected_net_revenue NUMERIC
min_model_confidence NUMERIC
recovery_window_hours INT
auto_action_probability NUMERIC
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## customers

```text
id UUID PK
merchant_id UUID FK
transaction_count INT
success_count INT
failure_count INT
avg_amount NUMERIC
preferred_method TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## payments

```text
id UUID PK
merchant_id UUID FK
customer_id UUID FK
external_payment_id TEXT UNIQUE
amount NUMERIC
currency TEXT
method TEXT
status TEXT
failure_code TEXT
attempt_number INT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## recovery_cases

```text
id UUID PK
merchant_id UUID FK
payment_id UUID FK
customer_id UUID FK
status TEXT
revenue_at_risk NUMERIC
selected_action TEXT
expected_gross_recovery NUMERIC
expected_net_revenue NUMERIC
actual_recovered NUMERIC
intervention_cost NUMERIC
incremental_recovery NUMERIC
net_incremental_recovery NUMERIC
requires_approval BOOLEAN
approval_status TEXT
model_name TEXT
model_version TEXT
policy_version TEXT
expires_at TIMESTAMPTZ
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## action_candidates

```text
id UUID PK
case_id UUID FK
action TEXT
probability NUMERIC
model_confidence NUMERIC
recoverable_amount NUMERIC
intervention_cost NUMERIC
incentive_cost NUMERIC
contact_cost NUMERIC
expected_gross_recovery NUMERIC
expected_net_revenue NUMERIC
allowed BOOLEAN
blocked_reason TEXT
rank INT
created_at TIMESTAMPTZ
```

## recovery_actions

```text
id UUID PK
case_id UUID FK
action TEXT
idempotency_key TEXT UNIQUE
status TEXT
attempt_number INT
requested_at TIMESTAMPTZ
executed_at TIMESTAMPTZ
result TEXT
recovered_amount NUMERIC
cost NUMERIC
provider_reference TEXT
error_code TEXT
error_message TEXT
created_at TIMESTAMPTZ
```

## audit_logs

```text
id UUID PK
case_id UUID FK
event_type TEXT
actor TEXT
source TEXT
input_snapshot JSONB
output_snapshot JSONB
decision JSONB
guardrail_result JSONB
model_name TEXT
model_version TEXT
policy_version TEXT
timestamp TIMESTAMPTZ
```

## experiment_runs

```text
id UUID PK
seed INT
dataset_size INT
baseline_policy TEXT
ai_policy TEXT
baseline_recovered NUMERIC
ai_recovered NUMERIC
baseline_cost NUMERIC
ai_cost NUMERIC
incremental_recovery NUMERIC
net_incremental_recovery NUMERIC
created_at TIMESTAMPTZ
```

## experiment_cases

```text
id UUID PK
experiment_id UUID FK
case_id UUID FK
baseline_action TEXT
baseline_success BOOLEAN
baseline_recovered NUMERIC
ai_action TEXT
ai_success BOOLEAN
ai_recovered NUMERIC
ai_cost NUMERIC
created_at TIMESTAMPTZ
```

## webhook_events

```text
id UUID PK
provider TEXT
external_event_id TEXT UNIQUE
event_type TEXT
payload JSONB
signature_valid BOOLEAN
processing_status TEXT
processed_at TIMESTAMPTZ
created_at TIMESTAMPTZ
```

---

# 8. FINANCIAL DEFINITIONS

## Expected gross recovery

```text
expected_gross_recovery(action)
=
P(success | context, action)
× recoverable_amount
```

## Expected net revenue

```text
expected_net_revenue(action)
=
expected_gross_recovery
-
intervention_cost
-
incentive_cost
-
contact_cost
```

## Actual recovery

```text
actual_recovered
=
payment_amount
if final verified payment status == SUCCESS
else 0
```

## Incremental recovery

```text
incremental_recovery
=
AI_recovered_revenue
-
baseline_recovered_revenue
```

## Net incremental recovery

```text
net_incremental_recovery
=
incremental_recovery
-
(AI_intervention_cost - baseline_intervention_cost)
```

Expected and actual values must never be mixed.

---

# 9. ML ARCHITECTURE

Implement a stable model interface from the beginning.

```python
class RecoveryOutcomeModel(Protocol):
    def predict_action_outcomes(
        self,
        case_context: CaseContext,
        actions: list[str],
    ) -> list[ActionPrediction]:
        ...
```

## Development model

Implement:

```text
RuleBasedRecoveryModel
```

first so the entire application can run without training infrastructure.

## Final model

Implement:

```text
XGBoostRecoveryModel
```

using:
- Python;
- pandas;
- scikit-learn;
- XGBoost.

The optimizer must not know which model generated predictions.

## Features

Use features such as:

```text
amount
payment_method
failure_code
attempt_number
customer_transaction_count
customer_success_count
customer_failure_count
customer_success_rate
customer_avg_amount
time_since_failure
hour_of_day
day_of_week
previous_failure_count
```

Never use post-action information as input features.

## Output

```json
{
  "action": "retry_later",
  "probability": 0.81,
  "confidence": 0.78,
  "model_name": "xgboost_recovery",
  "model_version": "xgb_v1"
}
```

## Evaluation

Report:
- precision;
- recall;
- F1;
- PR-AUC if practical;
- confusion matrix;
- calibration/error analysis if practical.

Do not claim real-world predictive performance from synthetic data.

---

# 10. SYNTHETIC DATA AND COUNTERFACTUAL SIMULATION

The simulator is a centerpiece.

Do not independently sample a fresh random outcome every time baseline and AI are evaluated.

## 10.1 Generate customers

Generate realistic distributions for:
- transaction count;
- success rate;
- average amount;
- preferred payment method.

Use a fixed random seed.

## 10.2 Generate payments

Generate:
- customer;
- amount;
- method;
- failure code;
- attempt number;
- timestamp.

## 10.3 Generate latent potential outcomes

Conceptually:

```text
customer quality
+ payment context
+ failure type
+ amount
+ action effect
+ timing
        ↓
latent probability of recovery
        ↓
potential outcome for each action
```

Example:

```text
case_123

retry_now      p=.61
retry_later    p=.79
reminder       p=.52
incentive      p=.87
escalate       p=.40
do_nothing     p=.08
```

Baseline and AI must consume the same potential-outcome environment.

## 10.4 Reproducibility

Support:

```json
{
  "rows": 10000,
  "seed": 42
}
```

Same seed must produce the same experiment.

---

# 11. BASELINE POLICY

Implement a fixed baseline:

```text
If payment failed:
    attempt immediate retry once
    if successful → recovered
    otherwise → stop
```

The baseline must not use:
- Gemini;
- ML optimization;
- dynamic incentives.

Its purpose is to provide a stable comparison.

---

# 12. OPTIMIZER

File:

```text
backend/optimizer/expected_value.py
```

Responsibilities:
1. accept action predictions;
2. calculate expected financial value;
3. rank actions;
4. return a deterministic result.

Example:

```python
OptimizationResult(
    selected_action="retry_later",
    candidates=[...],
    selected_expected_net_revenue=4049.0,
)
```

The optimizer:
- must include `do_nothing`;
- must rank only supplied actions;
- must never execute;
- must never call Gemini;
- must never bypass guardrails.

---

# 13. GUARDRAIL ENGINE

File:

```text
backend/guardrails/engine.py
```

Deterministic only.

Example policy:

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

## Hard checks

Apply in this order:

1. payment already successful → STOP;
2. case expired → EXPIRED;
3. duplicate action/idempotency conflict → STOP;
4. action not allowed → BLOCK;
5. retry limit reached → remove retry actions;
6. message limit reached → remove reminder;
7. customer incentive limit reached → remove incentive;
8. daily incentive pool exhausted → remove incentive;
9. high-value threshold reached → approval required;
10. required approval missing → PENDING_APPROVAL;
11. model confidence too low → ESCALATE or approval;
12. expected net revenue below minimum → DO_NOTHING.

After removing blocked actions, re-run optimization.

Every guardrail decision must be logged.

---

# 14. APPROVAL WORKFLOW

High-value or uncertain cases require approval.

```text
DECISION_READY
      ↓
high-value / uncertain
      ↓
PENDING_APPROVAL
      ↓
merchant approves
      ↓
APPROVED
      ↓
EXECUTING
```

Reject:

```text
PENDING_APPROVAL
      ↓
STOPPED
```

UI must show:
- amount;
- selected action;
- expected gross recovery;
- expected net revenue;
- probability;
- confidence;
- policy threshold;
- reason approval is required.

---

# 15. DECISION PROPOSAL CONTRACT

Create a shared domain object containing:

```text
case_id
recommended_action
candidate_actions
predictions
expected_values
selected_expected_net_revenue
reason
model_name
model_version
policy_version
guardrail_status
requires_approval
```

Backend code owns:
- authoritative action;
- expected values;
- guardrail result;
- approval state.

Preferred architecture:

```text
ML → probabilities
Optimizer → authoritative financial decision
Guardrails → permission
Gemini → explanation
```

If Gemini recommends something different from the optimizer, do not blindly accept it.

---

# 16. AGENT DESIGN

Use Gemini API with structured output/function calling where useful.

The agent is for reasoning and explanation.

## Read-only tools

```text
get_payment()
get_customer_history()
get_failure_context()
predict_action_outcomes()
get_recovery_budget()
calculate_expected_value()
check_policy()
```

## Never expose direct execution tools

Do not give the LLM direct access to:

```text
retry_payment()
send_recovery_message()
create_payment_link()
apply_incentive()
escalate_case()
stop_recovery()
```

Those are backend-controlled.

## Example output

```json
{
  "recommended_action": "retry_later",
  "reason": "Delayed retry has the highest expected net recovery among currently allowed actions.",
  "confidence": 0.81
}
```

The backend must validate this against the deterministic decision.

---

# 17. AGENT FALLBACK

If Gemini fails:
- continue with the deterministic optimizer;
- generate a simple template explanation.

Example:

```text
RecoveryOS selected retry_later because it has the highest expected net revenue among currently allowed actions.
```

Gemini must never be a hard dependency for financial correctness.

---

# 18. ACTION ADAPTERS

Create:

```text
backend/tools/
    retry.py
    reminder.py
    incentive.py
    escalation.py
    stop.py
    verification.py
```

Each adapter:
- accepts a validated request;
- checks idempotency;
- records execution state;
- returns a structured result;
- never chooses policy.

Example:

```python
ActionResult(
    success=True,
    provider_reference="test_ref",
    recovered_amount=4999,
    error=None
)
```

---

# 19. SIMULATION EXECUTION ADAPTER

For simulation, never call Razorpay.

Use:

```text
SimulationActionAdapter
```

It uses synthetic potential outcomes.

The same `RecoveryPipeline` is reused with a different execution adapter.

---

# 20. RAZORPAY INTEGRATION

Build after the simulator and core pipeline are stable.

Flow:

```text
Razorpay Test Mode
      ↓
payment.failed
      ↓
POST /webhooks/razorpay
      ↓
verify signature
      ↓
deduplicate event
      ↓
normalize payment
      ↓
create/update recovery case
      ↓
RecoveryPipeline
      ↓
guarded action
      ↓
verify current payment status
      ↓
audit
```

Required:
- public HTTPS endpoint;
- webhook secret in environment variables;
- signature validation;
- event idempotency;
- current payment-state recheck;
- no secret keys in frontend.

Use only test/synthetic data.

---

# 21. WEBHOOK IDEMPOTENCY

Use `webhook_events.external_event_id` as a unique key.

Processing:

```text
receive event
→ verify signature
→ check external_event_id
→ if already processed:
      return success/no-op
→ insert event
→ process
→ mark processed
```

Failed processing must not create duplicate financial actions.

---

# 22. ACTION IDEMPOTENCY

Every recovery action gets an idempotency key.

Example:

```text
{case_id}:{action}:{attempt_number}
```

Example:

```text
case_123:retry_now:1
```

Database uniqueness must prevent duplicate execution.

---

# 23. CONCURRENCY PROTECTION

Two requests must never execute the same case simultaneously.

Use an atomic state transition such as:

```sql
UPDATE recovery_cases
SET status='EXECUTING'
WHERE id=:case_id
AND status='APPROVED';
```

Only the successful transition may proceed to execution.

If no row is updated:
- do not execute;
- return the current case state.

---

# 24. VERIFICATION

Verification is mandatory.

After action:
1. query current payment status;
2. determine actual success;
3. record verification timestamp;
4. record provider reference;
5. calculate actual recovered amount.

Never infer recovery solely from an action API response.

---

# 25. AUDIT TRAIL

Recommended events:

```text
payment_failed
context_loaded
predictions_generated
optimization_completed
guardrail_passed
guardrail_blocked
approval_requested
approval_granted
approval_rejected
action_requested
action_executed
action_failed
verification_started
payment_recovered
verification_failed
case_stopped
case_escalated
case_expired
```

Each event should include:
- case ID;
- timestamp;
- actor;
- source;
- model version if relevant;
- policy version;
- structured input/output snapshots where safe.

---

# 26. MODEL AND POLICY VERSIONING

Every decision must store:

```text
model_name
model_version
policy_version
```

If practical, store a policy hash.

Old decisions must remain explainable after future model/policy changes.

---

# 27. API CONTRACTS

FastAPI is the only frontend/backend interface.

## Health

```http
GET /health
```

```json
{"status":"ok"}
```

## Dashboard

```http
GET /api/dashboard/summary
```

Return:
- revenue at risk;
- revenue recovered;
- baseline recovered;
- incremental recovery;
- intervention spend;
- net incremental recovery;
- recovery rate;
- guardrail stops;
- escalations.

## Cases

```http
GET /api/recovery-cases
GET /api/recovery-cases/{case_id}
```

Support basic filtering.

## Analyze

```http
POST /api/recovery-cases/{case_id}/analyze
```

Runs detection through guardrails but must not execute a money-moving action.

## Approval

```http
POST /api/recovery-cases/{case_id}/approve
POST /api/recovery-cases/{case_id}/reject
```

## Execute

```http
POST /api/recovery-cases/{case_id}/execute
```

Only valid if:
- decision exists;
- guardrails pass;
- approval requirement is satisfied;
- case is executable.

## Stop

```http
POST /api/recovery-cases/{case_id}/stop
```

## Audit

```http
GET /api/recovery-cases/{case_id}/audit
```

## Simulator

```http
POST /api/simulator/run
```

Request:

```json
{
  "rows": 10000,
  "seed": 42
}
```

Return experiment ID.

## Simulator result

```http
GET /api/simulator/{experiment_id}
```

## Razorpay webhook

```http
POST /webhooks/razorpay
```

Signature validation is mandatory.

---

# 28. API ERROR CONTRACT

Use:

```json
{
  "error": {
    "code": "CASE_NOT_EXECUTABLE",
    "message": "Case is waiting for approval.",
    "details": {}
  }
}
```

Never expose stack traces or secrets.

---

# 29. DASHBOARD REQUIREMENTS

Use:
- React;
- Vite;
- Tailwind CSS;
- Recharts.

## Command Center

Large metrics:
- Revenue at Risk;
- Revenue Recovered;
- Baseline Recovery;
- Incremental Recovery;
- Net Incremental Recovery.

## AI Recovery Queue

Show:
- case;
- amount;
- failure reason;
- predicted best action;
- expected net revenue;
- confidence;
- status;
- approval required.

## Case Detail

Show:
- payment amount;
- failure context;
- customer history;
- candidate probabilities;
- expected value per action;
- selected action;
- guardrail results;
- approval state;
- agent explanation;
- audit timeline.

## Simulator

Show:
- batch size;
- seed;
- baseline recovered;
- AI recovered;
- intervention cost;
- incremental recovery;
- net incremental recovery.

## Policy

Show current:
- retry limit;
- message limit;
- incentive budget;
- high-value threshold;
- recovery window;
- expected-value threshold;
- confidence threshold.

---

# 30. UI SAFETY

Execute button is enabled only if:

```text
case.status == APPROVED
OR
case.status == DECISION_READY AND approval is not required
```

If blocked, explain why.

Example:

```text
EXECUTION BLOCKED

Reason:
Daily incentive pool exhausted

RecoveryOS selected:
retry_later
```

---

# 31. SIMULATOR

Implement:

```text
simulator/
    baseline.py
    recovery_policy.py
    outcome_model.py
    experiments.py
    metrics.py
```

Run:
1. same batch through baseline;
2. same batch through RecoveryOS;
3. collect case outcomes;
4. aggregate metrics.

Return:
- baseline recovered;
- AI recovered;
- baseline cost;
- AI cost;
- incremental recovery;
- net incremental recovery;
- recovery rate;
- stopped count;
- escalated count.

Support multiple seeds for statistical evaluation.

---

# 32. EVALUATION

## Business metrics

```text
Revenue at Risk
Revenue Recovered
Recovery Rate
Recovery Value Rate
Intervention Cost
Incremental Recovery
Net Incremental Recovery
Guardrail Stop Rate
Escalation Rate
Average Recovery Time
```

## ML metrics

```text
Precision
Recall
F1
PR-AUC if practical
Confusion Matrix
Calibration/error analysis if practical
```

Do not fabricate results.

---

# 33. REPOSITORY STRUCTURE

```text
recovery-os/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.*
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── dashboard.py
│   │   ├── recovery_cases.py
│   │   ├── simulator.py
│   │   └── webhooks.py
│   ├── orchestrator/
│   │   └── recovery_pipeline.py
│   ├── domain/
│   │   ├── models.py
│   │   ├── enums.py
│   │   └── schemas.py
│   ├── agents/
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   ├── optimizer/
│   │   ├── expected_value.py
│   │   └── ranker.py
│   ├── guardrails/
│   │   ├── engine.py
│   │   ├── policies.py
│   │   └── approvals.py
│   ├── tools/
│   │   ├── retry.py
│   │   ├── reminder.py
│   │   ├── incentive.py
│   │   ├── escalation.py
│   │   ├── stop.py
│   │   └── verification.py
│   ├── services/
│   │   ├── payment_service.py
│   │   ├── customer_service.py
│   │   ├── prediction_service.py
│   │   └── audit_service.py
│   ├── webhooks/
│   │   └── razorpay.py
│   └── db/
│       ├── schema.sql
│       └── repositories/
├── ml/
│   ├── generate_data.py
│   ├── features.py
│   ├── outcome_generator.py
│   ├── train.py
│   ├── evaluate.py
│   └── artifacts/
├── simulator/
│   ├── baseline.py
│   ├── recovery_policy.py
│   ├── outcome_model.py
│   ├── experiments.py
│   └── metrics.py
├── policies/
│   └── recovery_policy.yaml
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── simulator/
│   └── api/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── demo.md
├── .env.example
├── requirements.txt
└── README.md
```

---

# 34. MODULE RESPONSIBILITIES

`orchestrator/` — owns workflow order.

`optimizer/` — owns financial calculations and ranking. Never executes.

`guardrails/` — owns safety and merchant policy. Deterministic only.

`agents/` — owns Gemini integration and explanations.

`tools/` — owns controlled actions. Never chooses which action is best.

`services/` — owns data/integration access.

`ml/` — owns training, synthetic data, features, evaluation.

`simulator/` — owns experiments and business-value evaluation.

`webhooks/` — owns provider event normalization and idempotency.

---

# 35. TESTING REQUIREMENTS

## Unit tests

Optimizer:
- ranking;
- cost handling;
- zero probability;
- do_nothing.

Guardrails:
- successful payment stops;
- retry limit blocks retry;
- message limit blocks reminder;
- incentive budget removes incentive;
- high-value requires approval;
- expired case stops;
- low expected value chooses do_nothing;
- low confidence escalates.

State machine:
- valid transitions;
- invalid transitions.

Idempotency:
- duplicate webhook does not duplicate action;
- duplicate execution does not execute twice.

Financial calculations:
- deterministic manually verifiable cases.

## Integration test

```text
case creation
→ pipeline
→ optimizer
→ guardrails
→ approval
→ execution adapter
→ verification
→ audit
```

## Simulator tests

- same seed → same output;
- baseline and AI → same batch;
- no fabricated metrics.

---

# 36. REQUIRED DEMO CASES

## Case A — Successful recovery

```text
failed payment
→ AI selects retry_later
→ guardrail PASS
→ execute
→ verify SUCCESS
→ RECOVERED
```

## Case B — Do nothing

```text
low-value payment
→ expected net value below threshold
→ do_nothing
→ STOPPED
```

## Case C — Guardrail block

```text
retry limit reached
→ retry blocked
→ alternative action or escalation
```

## Case D — Approval

```text
high-value payment
→ PENDING_APPROVAL
→ merchant approves
→ execute
→ verify
```

## Case E — Duplicate webhook

```text
same webhook twice
→ second event recognized
→ no duplicate action
```

---

# 37. FAILURE HANDLING

## ML unavailable

Use:

```text
RuleBasedRecoveryModel
```

## Gemini unavailable

Use:
- deterministic optimizer;
- template explanation.

## Database unavailable

Fail closed. Do not execute money-moving actions.

## Razorpay unavailable

Mark execution failure/unknown and never claim recovery.

## Verification unavailable

Set:

```text
UNKNOWN
```

not `RECOVERED`.

## Invalid policy

Fail closed and surface configuration error.

---

# 38. SECURITY

Never:
- commit `.env`;
- expose API secrets to frontend;
- expose Razorpay secret key to frontend;
- trust client-provided expected revenue;
- trust client-provided guardrail status;
- trust client-selected actions without backend validation;
- trust unsigned webhook payloads;
- store unnecessary sensitive customer information.

Backend is authoritative.

---

# 39. ENVIRONMENT VARIABLES

`.env.example`:

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

Never commit real values.

---

# 40. HOSTING

Target:

```text
Frontend → Vercel
Backend → Render
Database → Supabase
ML → Python/XGBoost backend
Agent → Gemini API
Payments → Razorpay Test Mode
```

Deployment order:
1. Supabase;
2. backend;
3. frontend;
4. webhook;
5. end-to-end test.

Keep the simulator usable even if live integrations are unavailable.

---

# 41. OPTIONAL RAG

RAG is optional and must come after the core loop.

If added, use it for merchant policy/context retrieval:
- recovery policy;
- escalation policy;
- incentive rules;
- merchant-specific operating rules.

RAG may provide context but must never bypass deterministic guardrails.

The structured policy remains authoritative.

---

# 42. OPTIONAL SHAP

SHAP may be added after the core ML pipeline.

Use:

```text
SHAP → model feature contribution
Gemini → human-readable case explanation
```

Do not confuse the two.

---

# 43. BUILD ORDER

## Phase 1 — Foundation

Create:
- repository;
- environment configuration;
- FastAPI app;
- Supabase schema;
- domain enums/schemas;
- health endpoint.

Done when backend starts and database connectivity/tests work.

## Phase 2 — Synthetic data

Create:
- customer generator;
- payment generator;
- latent outcome generator;
- reproducible seed.

Done when 1,000+ cases can be generated reproducibly.

## Phase 3 — Baseline

Implement fixed baseline.

Done when baseline metrics are reproducible.

## Phase 4 — ML

Create:
- model protocol;
- rule model;
- XGBoost model;
- evaluation.

Done when predictions use one interface and evaluation is documented.

## Phase 5 — Optimizer

Implement expected-value calculations and ranking.

Done when candidate actions are ranked and do_nothing works.

## Phase 6 — Guardrails

Implement:
- policy loader;
- guardrail engine;
- approval rules;
- state machine.

Done when safety test cases pass.

## Phase 7 — Recovery pipeline

Connect:

```text
context
→ prediction
→ optimizer
→ guard
→ approval
→ execution adapter
→ verification
→ audit
```

Done when one complete case works.

## Phase 8 — Simulator

Compare baseline vs RecoveryOS on the same batch.

Done when incremental net revenue is reproducible.

## Phase 9 — Agent

Add Gemini explanation.

Done when the explanation references actual case data and cannot execute actions.

## Phase 10 — Dashboard

Build:
- command center;
- queue;
- detail;
- simulator;
- audit timeline;
- approval UI.

Done when UI values match backend values.

## Phase 11 — Razorpay

Add:
- webhook;
- signature validation;
- idempotency;
- payment-state verification.

Done when a Test Mode event reaches the same pipeline.

## Phase 12 — Deployment

Deploy and run end-to-end tests.

Prepare fallback screenshots/video.

---

# 44. CODING-AGENT RULES

1. Read this file before coding.
2. Treat this file as the architecture source of truth.
3. Do not redesign the architecture unless explicitly instructed.
4. Build one phase at a time.
5. Run tests after every meaningful phase.
6. Do not leave placeholder functions silently returning fake success.
7. If an integration is unavailable, use a clearly named mock/simulation adapter.
8. Keep simulation and live execution adapters separate.
9. Keep financial calculations deterministic.
10. Keep LLM optional to financial correctness.
11. Add schemas/types before wiring modules together.
12. Reuse shared domain models.
13. Never duplicate business logic between simulator and webhook.
14. Never add action types casually.
15. Never bypass guardrails.
16. Never mark payment recovered without verification.
17. Never commit secrets.
18. Never claim live Razorpay behavior without actually testing Test Mode.
19. Never fabricate metrics.
20. Prefer simple, readable code over clever abstractions.

---

# 45. DO NOT BUILD

Do not build:
- multi-agent architecture;
- Kubernetes;
- Kafka;
- Redis;
- unnecessary microservices;
- unrestricted autonomous payment execution;
- direct LLM payment execution;
- a huge RAG system;
- voice assistant;
- unrelated revenue-leakage modules;
- production payment handling;
- real-money incentives;
- fake ML;
- fake benchmark results;
- fake Razorpay responses presented as live.

---

# 46. DEFINITION OF DONE

## Core
- synthetic data works;
- baseline works;
- optimizer works;
- expected net revenue works;
- do_nothing works;
- guardrails work;
- approval workflow works;
- verification works;
- audit trail works.

## ML
- model interface exists;
- XGBoost evaluated if included;
- evaluation reproducible;
- model version logged.

## Agent
- Gemini explains decisions;
- no direct money-moving execution;
- fallback works.

## Simulator
- same batch baseline vs AI;
- reproducible seed;
- incremental recovery;
- net incremental recovery;
- experiment stored.

## Dashboard
- command center;
- queue;
- detail;
- simulator;
- audit;
- approval.

## Razorpay
- Test Mode;
- signature validation;
- duplicate event protection;
- same RecoveryPipeline;
- payment-state verification.

## Deployment
- frontend public;
- backend public;
- database configured;
- secrets protected;
- `/health` works;
- simulator remains usable.

---

# 47. FINAL ACCEPTANCE TEST

Run before declaring the project complete.

### Test 1 — Reproducibility
Generate 10,000 cases with seed 42.

Expected:
- same dataset every time.

### Test 2 — Baseline
Expected:
- deterministic recovery metrics.

### Test 3 — RecoveryOS
Expected:
- deterministic recovery metrics.

### Test 4 — Business comparison
Expected:
- same batch;
- incremental recovery;
- net incremental recovery.

### Test 5 — High-value case
Expected:
- PENDING_APPROVAL.

### Test 6 — Retry-limit case
Expected:
- retry blocked.

### Test 7 — Low-value case
Expected:
- do_nothing.

### Test 8 — Successful recovery
Expected:
- payment verified;
- case RECOVERED;
- actual recovered amount recorded.

### Test 9 — Duplicate webhook
Expected:
- no duplicate action.

### Test 10 — Gemini unavailable
Expected:
- financial decision still works;
- fallback explanation appears.

### Test 11 — ML unavailable
Expected:
- deterministic fallback works.

### Test 12 — Invalid client request
Expected:
- backend rejects it;
- no financial action occurs.

---

# 48. JUDGE-FACING STORY

The application should make this sequence obvious:

```text
A payment failed.
        ↓
RecoveryOS understands the payment and customer.
        ↓
It predicts the outcome of multiple interventions.
        ↓
It converts probabilities into expected ₹ value.
        ↓
It applies merchant limits and safety rules.
        ↓
It can say NO.
        ↓
If action is allowed, it executes through a controlled adapter.
        ↓
It verifies whether money was actually recovered.
        ↓
It logs exactly what happened.
        ↓
Across a batch, it proves whether it recovered more
net revenue than a fixed baseline.
```

The key business question is:

> **“How much more net revenue can the merchant recover if AI chooses interventions intelligently instead of following a fixed retry rule?”**

---

# 49. FINAL ARCHITECTURAL PRINCIPLE

RecoveryOS is not primarily an LLM project.

It is:

```text
Revenue Decision Engine
+
ML Outcome Prediction
+
Expected-Value Optimization
+
Merchant Policy
+
Deterministic Guardrails
+
Bounded Agent Explanation
+
Controlled Execution
+
Verification
+
Measurable Incremental Revenue
```

The LLM is one component.
The optimizer is one component.
The ML model is one component.

The product is the **complete safe recovery loop**.

Build the smallest complete loop first. Reliability, measurable incremental revenue, safe stopping, and a clear audit trail are more valuable than adding more AI features.
