-- RecoveryOS — Database Schema
-- Target: Supabase PostgreSQL
-- Apply this file once via Supabase SQL editor or psql.
--
-- Tables:
--   merchants, customers, payments,
--   recovery_cases, action_candidates, recovery_actions,
--   audit_logs, experiment_runs, experiment_cases, webhook_events

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Merchants ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS merchants (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                        TEXT NOT NULL,
    retry_limit                 INT NOT NULL DEFAULT 2,
    message_limit               INT NOT NULL DEFAULT 2,
    max_incentive_per_customer  NUMERIC(12,2) NOT NULL DEFAULT 100.00,
    daily_incentive_pool        NUMERIC(12,2) NOT NULL DEFAULT 5000.00,
    high_value_threshold        NUMERIC(12,2) NOT NULL DEFAULT 10000.00,
    min_expected_net_revenue    NUMERIC(12,2) NOT NULL DEFAULT 100.00,
    min_model_confidence        NUMERIC(5,4)  NOT NULL DEFAULT 0.65,
    recovery_window_hours       INT           NOT NULL DEFAULT 48,
    auto_action_probability     NUMERIC(5,4)  NOT NULL DEFAULT 0.70,
    created_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ── Customers ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id         UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    transaction_count   INT NOT NULL DEFAULT 0,
    success_count       INT NOT NULL DEFAULT 0,
    failure_count       INT NOT NULL DEFAULT 0,
    avg_amount          NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    preferred_method    TEXT NOT NULL DEFAULT 'card',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_merchant_id ON customers(merchant_id);

-- ── Payments ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id         UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    external_payment_id TEXT UNIQUE NOT NULL,
    amount              NUMERIC(12,2) NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'INR',
    method              TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'failed',
    failure_code        TEXT NOT NULL DEFAULT 'unknown',
    attempt_number      INT NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_merchant_id ON payments(merchant_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer_id ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_external_id ON payments(external_payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- ── Recovery Cases ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recovery_cases (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id             UUID NOT NULL REFERENCES merchants(id),
    payment_id              UUID NOT NULL REFERENCES payments(id),
    customer_id             UUID NOT NULL REFERENCES customers(id),
    status                  TEXT NOT NULL DEFAULT 'CREATED',
    revenue_at_risk         NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    selected_action         TEXT,
    expected_gross_recovery NUMERIC(12,2),
    expected_net_revenue    NUMERIC(12,2),
    actual_recovered        NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    intervention_cost       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    incremental_recovery    NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    net_incremental_recovery NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    requires_approval       BOOLEAN NOT NULL DEFAULT FALSE,
    approval_status         TEXT NOT NULL DEFAULT 'not_required',
    model_name              TEXT,
    model_version           TEXT,
    policy_version          TEXT,
    expires_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recovery_cases_merchant_id ON recovery_cases(merchant_id);
CREATE INDEX IF NOT EXISTS idx_recovery_cases_payment_id ON recovery_cases(payment_id);
CREATE INDEX IF NOT EXISTS idx_recovery_cases_customer_id ON recovery_cases(customer_id);
CREATE INDEX IF NOT EXISTS idx_recovery_cases_status ON recovery_cases(status);
CREATE INDEX IF NOT EXISTS idx_recovery_cases_created_at ON recovery_cases(created_at DESC);

-- ── Action Candidates ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS action_candidates (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id                 UUID NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    action                  TEXT NOT NULL,
    probability             NUMERIC(5,4) NOT NULL,
    model_confidence        NUMERIC(5,4) NOT NULL,
    recoverable_amount      NUMERIC(12,2) NOT NULL,
    intervention_cost       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    incentive_cost          NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    contact_cost            NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    expected_gross_recovery NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    expected_net_revenue    NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allowed                 BOOLEAN NOT NULL DEFAULT TRUE,
    blocked_reason          TEXT,
    rank                    INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_candidates_case_id ON action_candidates(case_id);

-- ── Recovery Actions ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recovery_actions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    action              TEXT NOT NULL,
    idempotency_key     TEXT NOT NULL UNIQUE,   -- enforces no duplicate execution
    status              TEXT NOT NULL DEFAULT 'pending',
    attempt_number      INT NOT NULL DEFAULT 1,
    requested_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at         TIMESTAMPTZ,
    result              TEXT,
    recovered_amount    NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    cost                NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    provider_reference  TEXT,
    error_code          TEXT,
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recovery_actions_case_id ON recovery_actions(case_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recovery_actions_idempotency ON recovery_actions(idempotency_key);

-- ── Audit Logs ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id          UUID NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    event_type       TEXT NOT NULL,
    actor            TEXT NOT NULL DEFAULT 'system',
    source           TEXT NOT NULL DEFAULT 'system',
    input_snapshot   JSONB NOT NULL DEFAULT '{}',
    output_snapshot  JSONB NOT NULL DEFAULT '{}',
    decision         JSONB,
    guardrail_result JSONB,
    model_name       TEXT,
    model_version    TEXT,
    policy_version   TEXT,
    timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_case_id ON audit_logs(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);

-- ── Experiment Runs ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS experiment_runs (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seed                     INT NOT NULL,
    dataset_size             INT NOT NULL,
    baseline_policy          TEXT NOT NULL DEFAULT 'immediate_retry',
    ai_policy                TEXT NOT NULL DEFAULT 'recoveryos_v1',
    baseline_recovered       NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    ai_recovered             NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    baseline_cost            NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    ai_cost                  NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    incremental_recovery     NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    net_incremental_recovery NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    baseline_recovery_rate   NUMERIC(5,4) NOT NULL DEFAULT 0.00,
    ai_recovery_rate         NUMERIC(5,4) NOT NULL DEFAULT 0.00,
    guardrail_stops          INT NOT NULL DEFAULT 0,
    escalations              INT NOT NULL DEFAULT 0,
    do_nothing_count         INT NOT NULL DEFAULT 0,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiment_runs_seed ON experiment_runs(seed);
CREATE INDEX IF NOT EXISTS idx_experiment_runs_created_at ON experiment_runs(created_at DESC);

-- ── Experiment Cases ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS experiment_cases (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id       UUID NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
    case_id             UUID NOT NULL REFERENCES recovery_cases(id) ON DELETE CASCADE,
    baseline_action     TEXT NOT NULL,
    baseline_success    BOOLEAN NOT NULL DEFAULT FALSE,
    baseline_recovered  NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    ai_action           TEXT NOT NULL,
    ai_success          BOOLEAN NOT NULL DEFAULT FALSE,
    ai_recovered        NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    ai_cost             NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiment_cases_experiment_id ON experiment_cases(experiment_id);

-- ── Webhook Events ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS webhook_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider            TEXT NOT NULL DEFAULT 'razorpay',
    external_event_id   TEXT NOT NULL UNIQUE,   -- idempotency: duplicate events ignored
    event_type          TEXT NOT NULL,
    payload             JSONB NOT NULL DEFAULT '{}',
    signature_valid     BOOLEAN NOT NULL DEFAULT FALSE,
    processing_status   TEXT NOT NULL DEFAULT 'received',
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_events_external_id ON webhook_events(external_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processing_status ON webhook_events(processing_status);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at DESC);

-- ── Seed default merchant ─────────────────────────────────────────────────────
-- Insert a default merchant record for development/demo
INSERT INTO merchants (
    id,
    name,
    retry_limit,
    message_limit,
    max_incentive_per_customer,
    daily_incentive_pool,
    high_value_threshold,
    min_expected_net_revenue,
    min_model_confidence,
    recovery_window_hours,
    auto_action_probability
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Demo Merchant',
    2,
    2,
    100.00,
    5000.00,
    10000.00,
    100.00,
    0.65,
    48,
    0.70
) ON CONFLICT (id) DO NOTHING;
