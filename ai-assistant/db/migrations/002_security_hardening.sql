-- ============================================================================
-- 002_security_hardening.sql
-- Additive migration: risk levels, approval expiry, TOTP enrollment,
-- idempotency keys, execution leases, append-only audit log.
--
-- Safe to re-run (IF NOT EXISTS / guarded DO blocks). No destructive DDL.
-- Apply with:
--   docker exec -i ai-postgres psql -U ai -d ai < db/migrations/002_security_hardening.sql
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- approval_requests: risk level, approval level, expiry
-- ---------------------------------------------------------------------------
ALTER TABLE approval_requests
    ADD COLUMN IF NOT EXISTS risk_level VARCHAR(16) NOT NULL DEFAULT 'medium';

ALTER TABLE approval_requests
    ADD COLUMN IF NOT EXISTS approval_level VARCHAR(1) NOT NULL DEFAULT 'B';

ALTER TABLE approval_requests
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

UPDATE approval_requests
SET expires_at = requested_at + INTERVAL '60 minutes'
WHERE expires_at IS NULL;

ALTER TABLE approval_requests
    ALTER COLUMN expires_at SET DEFAULT (NOW() + INTERVAL '60 minutes');

ALTER TABLE approval_requests
    ALTER COLUMN expires_at SET NOT NULL;

ALTER TABLE approval_requests
    DROP CONSTRAINT IF EXISTS approval_requests_risk_level_check;
ALTER TABLE approval_requests
    ADD CONSTRAINT approval_requests_risk_level_check
    CHECK (risk_level IN ('low', 'medium', 'high', 'critical'));

ALTER TABLE approval_requests
    DROP CONSTRAINT IF EXISTS approval_requests_approval_level_check;
ALTER TABLE approval_requests
    ADD CONSTRAINT approval_requests_approval_level_check
    CHECK (approval_level IN ('A', 'B', 'C', 'D'));

CREATE INDEX IF NOT EXISTS idx_approval_requests_expires_at
    ON approval_requests (expires_at);

-- ---------------------------------------------------------------------------
-- audit_logs: task correlation and risk metadata
-- ---------------------------------------------------------------------------
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS risk_level VARCHAR(16);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS failure_reason TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'audit_logs_task_id_fkey'
    ) THEN
        ALTER TABLE audit_logs
            ADD CONSTRAINT audit_logs_task_id_fkey
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_audit_logs_task_id ON audit_logs (task_id);

-- ---------------------------------------------------------------------------
-- audit_logs: append-only enforcement
-- The application role owns the table, so GRANT/REVOKE alone cannot protect
-- it. A trigger rejects UPDATE/DELETE unless maintenance explicitly opts in
-- with: SET LOCAL app.allow_audit_mutation = 'on';
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF current_setting('app.allow_audit_mutation', true) = 'on' THEN
        RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
    END IF;
    RAISE EXCEPTION 'audit_logs is append-only (attempted %)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;
CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();

-- ---------------------------------------------------------------------------
-- idempotency_keys: exactly-once request handling
-- A key is globally unique; user_id and request_hash detect cross-user reuse
-- and payload changes. Completed responses are replayed to the caller.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR(128) NOT NULL,
    key VARCHAR(255) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed')),
    response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    CONSTRAINT idempotency_keys_key_unique UNIQUE (key)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires_at
    ON idempotency_keys (expires_at);

-- ---------------------------------------------------------------------------
-- approval_tokens: TOTP enrollment (second factor for level D actions)
-- One enrollment per user; the shared secret is stored encrypted with a key
-- derived from API_SECRET_KEY. last_counter prevents replay inside a window.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approval_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    secret_enc TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_counter BIGINT NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    CONSTRAINT approval_tokens_user_unique UNIQUE (user_id)
);

-- ---------------------------------------------------------------------------
-- task_executions: lease + heartbeat + bounded recovery
-- Recovery uses FOR UPDATE SKIP LOCKED so only one worker can adopt a stale
-- lease. recovery_count is capped; the sweep marks exhausted rows abandoned.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    idempotency_key VARCHAR(255),
    worker_id VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'recovered', 'completed', 'failed', 'abandoned')),
    attempt INTEGER NOT NULL DEFAULT 1,
    recovery_count INTEGER NOT NULL DEFAULT 0,
    lease_until TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    failure_reason TEXT,
    result JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_task_executions_lease
    ON task_executions (status, lease_until);

CREATE INDEX IF NOT EXISTS idx_task_executions_task_id
    ON task_executions (task_id);

COMMIT;
