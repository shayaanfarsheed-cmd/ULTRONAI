CREATE SCHEMA IF NOT EXISTS training_api;

REVOKE ALL ON SCHEMA training_api FROM PUBLIC;
REVOKE ALL ON SCHEMA training_api FROM anon;
GRANT USAGE ON SCHEMA training_api TO authenticated, service_role;

CREATE TABLE IF NOT EXISTS training_api.training_status (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    current_server text,
    current_step bigint NOT NULL DEFAULT 0 CHECK (current_step >= 0),
    current_topic text,
    difficulty smallint NOT NULL DEFAULT 1 CHECK (difficulty >= 1),
    data_position bigint NOT NULL DEFAULT 0 CHECK (data_position >= 0),
    data_epoch bigint NOT NULL DEFAULT 0 CHECK (data_epoch >= 0),
    loss double precision,
    accuracy_by_topic jsonb NOT NULL DEFAULT '{}'::jsonb,
    curriculum_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    learning_rate double precision,
    last_checkpoint_id text,
    last_checkpoint_at timestamptz,
    last_checkpoint_size_bytes bigint CHECK (last_checkpoint_size_bytes IS NULL OR last_checkpoint_size_bytes >= 0),
    last_checkpoint_verified boolean NOT NULL DEFAULT false,
    last_heartbeat_at timestamptz,
    session_started_at timestamptz,
    session_limit_seconds integer CHECK (session_limit_seconds IS NULL OR session_limit_seconds > 0),
    session_time_left_seconds integer CHECK (session_time_left_seconds IS NULL OR session_time_left_seconds >= 0),
    state text NOT NULL DEFAULT 'paused' CHECK (state IN ('starting', 'running', 'waiting_for_lease', 'handoff_needed', 'paused', 'finished', 'dead')),
    lease_holder text,
    lease_expires_at timestamptz,
    fencing_token bigint NOT NULL DEFAULT 0 CHECK (fencing_token >= 0),
    pause_requested boolean NOT NULL DEFAULT false,
    automatic_start_enabled boolean NOT NULL DEFAULT false,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((lease_holder IS NULL) = (lease_expires_at IS NULL))
);

CREATE TABLE IF NOT EXISTS training_api.server_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    run_id uuid NOT NULL REFERENCES training_api.training_status(run_id) ON DELETE CASCADE,
    session_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    server_name text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    gpu_seconds numeric(14,3) NOT NULL DEFAULT 0 CHECK (gpu_seconds >= 0),
    end_reason text CHECK (end_reason IS NULL OR end_reason IN ('finished', 'handoff', 'quota', 'kicked_out', 'crashed', 'user_stop', 'manual_entry', 'unknown')),
    manual boolean NOT NULL DEFAULT false,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE TABLE IF NOT EXISTS training_api.switch_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    run_id uuid REFERENCES training_api.training_status(run_id) ON DELETE CASCADE,
    from_server text,
    to_server text,
    reason text NOT NULL CHECK (reason IN ('handoff_needed', 'heartbeat_timeout', 'quota', 'no_gpu', 'slow_gpu', 'user_requested', 'failed_start', 'cpu_fallback', 'pause', 'resume')),
    requested_at timestamptz NOT NULL DEFAULT now(),
    result text NOT NULL DEFAULT 'waiting' CHECK (result IN ('waiting', 'started', 'failed', 'done')),
    started_at timestamptz,
    completed_at timestamptz,
    failure_reason text,
    automatic boolean NOT NULL DEFAULT false,
    attempt_number smallint NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    idempotency_key text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);

CREATE INDEX IF NOT EXISTS training_status_owner_heartbeat_idx
    ON training_api.training_status(owner_id, last_heartbeat_at DESC);

CREATE INDEX IF NOT EXISTS server_log_owner_started_idx
    ON training_api.server_log(owner_id, started_at DESC);

CREATE INDEX IF NOT EXISTS switch_requests_owner_requested_idx
    ON training_api.switch_requests(owner_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS switch_requests_waiting_idx
    ON training_api.switch_requests(result, requested_at)
    WHERE result = 'waiting';

CREATE UNIQUE INDEX IF NOT EXISTS training_status_one_lease_per_owner_idx
    ON training_api.training_status(owner_id)
    WHERE lease_holder IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS switch_requests_owner_idempotency_idx
    ON training_api.switch_requests(owner_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

ALTER TABLE training_api.training_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_api.server_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_api.switch_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS training_status_owner_select ON training_api.training_status;
CREATE POLICY training_status_owner_select
    ON training_api.training_status
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) IS NOT NULL AND owner_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS server_log_owner_select ON training_api.server_log;
CREATE POLICY server_log_owner_select
    ON training_api.server_log
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) IS NOT NULL AND owner_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS server_log_owner_manual_insert ON training_api.server_log;
CREATE POLICY server_log_owner_manual_insert
    ON training_api.server_log
    FOR INSERT
    TO authenticated
    WITH CHECK (
        (SELECT auth.uid()) IS NOT NULL
        AND owner_id = (SELECT auth.uid())
        AND manual = true
        AND end_reason = 'manual_entry'
    );

DROP POLICY IF EXISTS switch_requests_owner_select ON training_api.switch_requests;
CREATE POLICY switch_requests_owner_select
    ON training_api.switch_requests
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) IS NOT NULL AND owner_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS switch_requests_owner_insert ON training_api.switch_requests;
CREATE POLICY switch_requests_owner_insert
    ON training_api.switch_requests
    FOR INSERT
    TO authenticated
    WITH CHECK (
        (SELECT auth.uid()) IS NOT NULL
        AND owner_id = (SELECT auth.uid())
        AND automatic = false
        AND result = 'waiting'
    );

REVOKE ALL ON ALL TABLES IN SCHEMA training_api FROM anon, authenticated;
GRANT SELECT ON training_api.training_status, training_api.server_log, training_api.switch_requests TO authenticated;
GRANT INSERT ON training_api.server_log, training_api.switch_requests TO authenticated;
GRANT ALL ON training_api.training_status, training_api.server_log, training_api.switch_requests TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA training_api REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA training_api GRANT ALL ON TABLES TO service_role;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'checkpoints',
    'checkpoints',
    false,
    45000000,
    ARRAY['application/octet-stream', 'application/json']
)
ON CONFLICT (id) DO UPDATE
SET public = false,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ultron_checkpoint_owner_read ON storage.objects;
CREATE POLICY ultron_checkpoint_owner_read
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'checkpoints'
        AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
    );

GRANT SELECT ON storage.objects TO authenticated;
