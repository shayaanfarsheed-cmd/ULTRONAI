ALTER TABLE training_api.training_status
  ADD COLUMN IF NOT EXISTS active_session_id uuid,
  ADD COLUMN IF NOT EXISTS last_checkpoint_manifest_sha256 text,
  ADD COLUMN IF NOT EXISTS requested_resume_checkpoint_id text;

GRANT UPDATE (requested_resume_checkpoint_id) ON training_api.training_status TO authenticated;

CREATE OR REPLACE FUNCTION training_api.get_or_create_active_run(p_owner_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_row training_api.training_status%ROWTYPE;
BEGIN
  IF p_owner_id IS NULL THEN
    RAISE EXCEPTION 'owner_id is required';
  END IF;

  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_owner_id::text, 0));

  SELECT *
  INTO v_row
  FROM training_api.training_status
  WHERE owner_id = p_owner_id
    AND state <> 'finished'
  ORDER BY created_at DESC
  LIMIT 1
  FOR UPDATE;

  IF NOT FOUND THEN
    INSERT INTO training_api.training_status (owner_id, state)
    VALUES (p_owner_id, 'paused')
    RETURNING * INTO v_row;
  END IF;

  RETURN pg_catalog.jsonb_build_object(
    'run_id', v_row.run_id,
    'owner_id', v_row.owner_id,
    'state', v_row.state,
    'current_step', v_row.current_step,
    'current_topic', v_row.current_topic
  );
END;
$$;

CREATE OR REPLACE FUNCTION training_api.acquire_training_lease(
  p_run_id uuid,
  p_owner_id uuid,
  p_server_id text,
  p_worker_id text,
  p_device text,
  p_session_limit_seconds integer,
  p_ttl_seconds integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_row training_api.training_status%ROWTYPE;
  v_other training_api.training_status%ROWTYPE;
  v_session_id uuid;
  v_token bigint;
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_run_id IS NULL OR p_owner_id IS NULL OR NULLIF(p_server_id, '') IS NULL OR NULLIF(p_worker_id, '') IS NULL THEN
    RAISE EXCEPTION 'run, owner, server and worker identifiers are required';
  END IF;
  IF p_ttl_seconds IS NULL OR p_ttl_seconds < 60 OR p_ttl_seconds > 3600 THEN
    RAISE EXCEPTION 'lease TTL must be between 60 and 3600 seconds';
  END IF;
  IF p_session_limit_seconds IS NOT NULL AND p_session_limit_seconds < 60 THEN
    RAISE EXCEPTION 'session limit must be null or at least 60 seconds';
  END IF;

  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_owner_id::text, 0));

  FOR v_other IN
    SELECT *
    FROM training_api.training_status
    WHERE owner_id = p_owner_id
      AND run_id <> p_run_id
      AND lease_holder IS NOT NULL
    FOR UPDATE
  LOOP
    IF v_other.lease_expires_at > v_now THEN
      RETURN pg_catalog.jsonb_build_object(
        'granted', false,
        'reason', 'another_run_lease_held',
        'run_id', v_other.run_id,
        'lease_holder', v_other.lease_holder,
        'lease_expires_at', v_other.lease_expires_at,
        'fencing_token', v_other.fencing_token
      );
    END IF;

    IF v_other.active_session_id IS NOT NULL THEN
      UPDATE training_api.server_log
      SET ended_at = v_now,
          end_reason = 'crashed',
          gpu_seconds = CASE
            WHEN details->>'device' = 'cuda'
            THEN greatest(gpu_seconds, extract(epoch FROM (v_now - started_at)))
            ELSE gpu_seconds
          END,
          details = details || pg_catalog.jsonb_build_object('lease_expired', true)
      WHERE session_id = v_other.active_session_id
        AND ended_at IS NULL;
    END IF;

    UPDATE training_api.training_status
    SET lease_holder = NULL,
        lease_expires_at = NULL,
        active_session_id = NULL,
        state = 'dead',
        updated_at = v_now
    WHERE run_id = v_other.run_id;
  END LOOP;

  SELECT *
  INTO v_row
  FROM training_api.training_status
  WHERE run_id = p_run_id AND owner_id = p_owner_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RETURN pg_catalog.jsonb_build_object('granted', false, 'reason', 'run_not_found');
  END IF;

  IF v_row.lease_holder = p_worker_id AND v_row.lease_expires_at > v_now THEN
    UPDATE training_api.training_status
    SET lease_expires_at = v_now + pg_catalog.make_interval(secs => p_ttl_seconds),
        last_heartbeat_at = v_now,
        updated_at = v_now
    WHERE run_id = p_run_id
    RETURNING * INTO v_row;

    RETURN pg_catalog.jsonb_build_object(
      'granted', true,
      'run_id', v_row.run_id,
      'worker_id', v_row.lease_holder,
      'fencing_token', v_row.fencing_token,
      'lease_expires_at', v_row.lease_expires_at,
      'session_id', v_row.active_session_id,
      'idempotent_retry', true
    );
  END IF;

  IF v_row.lease_holder IS NOT NULL AND v_row.lease_expires_at > v_now THEN
    RETURN pg_catalog.jsonb_build_object(
      'granted', false,
      'reason', 'lease_held',
      'lease_holder', v_row.lease_holder,
      'lease_expires_at', v_row.lease_expires_at,
      'fencing_token', v_row.fencing_token
    );
  END IF;

  IF v_row.active_session_id IS NOT NULL THEN
    UPDATE training_api.server_log
    SET ended_at = v_now,
        end_reason = 'crashed',
        gpu_seconds = CASE
          WHEN details->>'device' = 'cuda'
          THEN greatest(gpu_seconds, extract(epoch FROM (v_now - started_at)))
          ELSE gpu_seconds
        END,
        details = details || pg_catalog.jsonb_build_object('lease_expired', true)
    WHERE session_id = v_row.active_session_id
      AND ended_at IS NULL;
  END IF;

  v_token := v_row.fencing_token + 1;
  v_session_id := pg_catalog.gen_random_uuid();

  INSERT INTO training_api.server_log (
    owner_id, run_id, session_id, server_name, started_at, details
  )
  VALUES (
    p_owner_id,
    p_run_id,
    v_session_id,
    p_server_id,
    v_now,
    pg_catalog.jsonb_build_object('worker_id', p_worker_id, 'device', coalesce(p_device, 'cpu'))
  );

  UPDATE training_api.training_status
  SET current_server = p_server_id,
      lease_holder = p_worker_id,
      lease_expires_at = v_now + pg_catalog.make_interval(secs => p_ttl_seconds),
      fencing_token = v_token,
      active_session_id = v_session_id,
      session_started_at = v_now,
      session_limit_seconds = p_session_limit_seconds,
      session_time_left_seconds = p_session_limit_seconds,
      last_heartbeat_at = v_now,
      state = 'running',
      pause_requested = false,
      handoff_requested = false,
      last_error = NULL,
      updated_at = v_now
  WHERE run_id = p_run_id
  RETURNING * INTO v_row;

  RETURN pg_catalog.jsonb_build_object(
    'granted', true,
    'run_id', v_row.run_id,
    'worker_id', v_row.lease_holder,
    'fencing_token', v_row.fencing_token,
    'lease_expires_at', v_row.lease_expires_at,
    'session_id', v_row.active_session_id,
    'idempotent_retry', false
  );
END;
$$;

CREATE OR REPLACE FUNCTION training_api.heartbeat_training_lease(
  p_run_id uuid,
  p_owner_id uuid,
  p_worker_id text,
  p_fencing_token bigint,
  p_ttl_seconds integer,
  p_current_step bigint,
  p_loss double precision,
  p_learning_rate double precision,
  p_current_topic text,
  p_difficulty smallint,
  p_data_position bigint,
  p_data_epoch bigint,
  p_accuracy_by_topic jsonb,
  p_curriculum_state jsonb,
  p_session_time_left_seconds integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_row training_api.training_status%ROWTYPE;
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_ttl_seconds IS NULL OR p_ttl_seconds < 60 OR p_ttl_seconds > 3600 THEN
    RAISE EXCEPTION 'lease TTL must be between 60 and 3600 seconds';
  END IF;

  UPDATE training_api.training_status
  SET lease_expires_at = v_now + pg_catalog.make_interval(secs => p_ttl_seconds),
      last_heartbeat_at = v_now,
      current_step = greatest(current_step, p_current_step),
      loss = p_loss,
      learning_rate = p_learning_rate,
      current_topic = p_current_topic,
      difficulty = greatest(1, p_difficulty),
      data_position = greatest(0, p_data_position),
      data_epoch = greatest(0, p_data_epoch),
      accuracy_by_topic = coalesce(p_accuracy_by_topic, accuracy_by_topic),
      curriculum_state = coalesce(p_curriculum_state, curriculum_state),
      session_time_left_seconds = CASE
        WHEN p_session_time_left_seconds IS NULL THEN session_time_left_seconds
        ELSE greatest(0, p_session_time_left_seconds)
      END,
      updated_at = v_now
  WHERE run_id = p_run_id
    AND owner_id = p_owner_id
    AND lease_holder = p_worker_id
    AND fencing_token = p_fencing_token
    AND lease_expires_at > v_now
  RETURNING * INTO v_row;

  IF NOT FOUND THEN
    RETURN pg_catalog.jsonb_build_object('ok', false, 'reason', 'lease_lost');
  END IF;

  UPDATE training_api.server_log
  SET gpu_seconds = CASE
    WHEN details->>'device' = 'cuda'
    THEN greatest(gpu_seconds, extract(epoch FROM (v_now - started_at)))
    ELSE gpu_seconds
  END
  WHERE session_id = v_row.active_session_id AND ended_at IS NULL;

  RETURN pg_catalog.jsonb_build_object(
    'ok', true,
    'pause_requested', v_row.pause_requested,
    'handoff_requested', v_row.handoff_requested,
    'automatic_start_enabled', v_row.automatic_start_enabled,
    'state', v_row.state,
    'lease_expires_at', v_row.lease_expires_at
  );
END;
$$;

DROP FUNCTION IF EXISTS training_api.commit_training_checkpoint(uuid, uuid, text, bigint, text, bigint, bigint, text);

CREATE OR REPLACE FUNCTION training_api.commit_training_checkpoint(
  p_run_id uuid,
  p_owner_id uuid,
  p_worker_id text,
  p_fencing_token bigint,
  p_checkpoint_id text,
  p_step bigint,
  p_size_bytes bigint,
  p_manifest_sha256 text,
  p_current_topic text,
  p_difficulty smallint,
  p_data_position bigint,
  p_data_epoch bigint,
  p_loss double precision,
  p_learning_rate double precision,
  p_accuracy_by_topic jsonb,
  p_curriculum_state jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_row training_api.training_status%ROWTYPE;
BEGIN
  IF p_checkpoint_id IS NULL OR p_checkpoint_id !~ '^ckpt-[a-zA-Z0-9-]{8,80}$' THEN
    RAISE EXCEPTION 'invalid checkpoint id';
  END IF;
  IF p_step IS NULL OR p_step < 0 OR p_size_bytes IS NULL OR p_size_bytes < 1
     OR p_manifest_sha256 IS NULL OR p_manifest_sha256 !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'invalid checkpoint metadata';
  END IF;

  UPDATE training_api.training_status
  SET last_checkpoint_id = p_checkpoint_id,
      last_checkpoint_step = p_step,
      last_checkpoint_at = v_now,
      last_checkpoint_size_bytes = p_size_bytes,
      last_checkpoint_verified = true,
      last_checkpoint_manifest_sha256 = p_manifest_sha256,
      current_step = greatest(current_step, p_step),
      current_topic = p_current_topic,
      difficulty = greatest(1, p_difficulty),
      data_position = greatest(0, p_data_position),
      data_epoch = greatest(0, p_data_epoch),
      loss = p_loss,
      learning_rate = p_learning_rate,
      accuracy_by_topic = coalesce(p_accuracy_by_topic, accuracy_by_topic),
      curriculum_state = coalesce(p_curriculum_state, curriculum_state),
      last_heartbeat_at = v_now,
      updated_at = v_now
  WHERE run_id = p_run_id
    AND owner_id = p_owner_id
    AND lease_holder = p_worker_id
    AND fencing_token = p_fencing_token
    AND lease_expires_at > v_now
    AND (last_checkpoint_step IS NULL OR p_step >= last_checkpoint_step)
  RETURNING * INTO v_row;

  IF NOT FOUND THEN
    RETURN pg_catalog.jsonb_build_object('ok', false, 'reason', 'lease_lost_or_checkpoint_regression');
  END IF;

  RETURN pg_catalog.jsonb_build_object(
    'ok', true,
    'checkpoint_id', v_row.last_checkpoint_id,
    'step', v_row.last_checkpoint_step,
    'verified', v_row.last_checkpoint_verified,
    'manifest_sha256', v_row.last_checkpoint_manifest_sha256
  );
END;
$$;

CREATE OR REPLACE FUNCTION training_api.release_training_lease(
  p_run_id uuid,
  p_owner_id uuid,
  p_worker_id text,
  p_fencing_token bigint,
  p_end_reason text,
  p_final_state text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_row training_api.training_status%ROWTYPE;
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_end_reason IS NULL OR p_end_reason NOT IN ('finished', 'handoff', 'quota', 'kicked_out', 'crashed', 'user_stop', 'unknown') THEN
    RAISE EXCEPTION 'invalid session end reason';
  END IF;
  IF p_final_state IS NULL OR p_final_state NOT IN ('handoff_needed', 'paused', 'finished', 'dead') THEN
    RAISE EXCEPTION 'invalid final training state';
  END IF;

  SELECT *
  INTO v_row
  FROM training_api.training_status
  WHERE run_id = p_run_id
    AND owner_id = p_owner_id
    AND lease_holder = p_worker_id
    AND fencing_token = p_fencing_token
  FOR UPDATE;

  IF NOT FOUND THEN
    RETURN pg_catalog.jsonb_build_object('ok', false, 'reason', 'lease_lost');
  END IF;

  IF v_row.active_session_id IS NOT NULL THEN
    UPDATE training_api.server_log
    SET ended_at = v_now,
        end_reason = p_end_reason,
        gpu_seconds = CASE
          WHEN details->>'device' = 'cuda'
          THEN greatest(gpu_seconds, extract(epoch FROM (v_now - started_at)))
          ELSE gpu_seconds
        END
    WHERE session_id = v_row.active_session_id
      AND ended_at IS NULL;
  END IF;

  UPDATE training_api.training_status
  SET lease_holder = NULL,
      lease_expires_at = NULL,
      active_session_id = NULL,
      state = p_final_state,
      pause_requested = false,
      handoff_requested = (p_final_state = 'handoff_needed'),
      session_time_left_seconds = CASE
        WHEN p_final_state = 'finished' THEN 0
        ELSE session_time_left_seconds
      END,
      last_heartbeat_at = v_now,
      updated_at = v_now
  WHERE run_id = p_run_id
  RETURNING * INTO v_row;

  RETURN pg_catalog.jsonb_build_object(
    'ok', true,
    'state', v_row.state,
    'current_step', v_row.current_step,
    'lease_released', true
  );
END;
$$;

REVOKE ALL ON FUNCTION training_api.get_or_create_active_run(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION training_api.acquire_training_lease(uuid, uuid, text, text, text, integer, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION training_api.heartbeat_training_lease(uuid, uuid, text, bigint, integer, bigint, double precision, double precision, text, smallint, bigint, bigint, jsonb, jsonb, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION training_api.commit_training_checkpoint(uuid, uuid, text, bigint, text, bigint, bigint, text, text, smallint, bigint, bigint, double precision, double precision, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION training_api.release_training_lease(uuid, uuid, text, bigint, text, text) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION training_api.get_or_create_active_run(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION training_api.acquire_training_lease(uuid, uuid, text, text, text, integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION training_api.heartbeat_training_lease(uuid, uuid, text, bigint, integer, bigint, double precision, double precision, text, smallint, bigint, bigint, jsonb, jsonb, integer) TO service_role;
GRANT EXECUTE ON FUNCTION training_api.commit_training_checkpoint(uuid, uuid, text, bigint, text, bigint, bigint, text, text, smallint, bigint, bigint, double precision, double precision, jsonb, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION training_api.release_training_lease(uuid, uuid, text, bigint, text, text) TO service_role;



CREATE OR REPLACE FUNCTION training_api.select_resume_checkpoint(
  p_run_id uuid,
  p_owner_id uuid,
  p_worker_id text,
  p_fencing_token bigint,
  p_checkpoint_id text,
  p_step bigint,
  p_size_bytes bigint,
  p_manifest_sha256 text,
  p_current_topic text,
  p_difficulty smallint,
  p_data_position bigint,
  p_data_epoch bigint,
  p_loss double precision,
  p_learning_rate double precision,
  p_accuracy_by_topic jsonb,
  p_curriculum_state jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $ultron$
DECLARE
  v_row training_api.training_status%ROWTYPE;
  v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
  IF p_checkpoint_id IS NULL OR p_checkpoint_id !~ '^ckpt-[a-zA-Z0-9-]{8,80}$'
     OR p_step IS NULL OR p_step < 0
     OR p_size_bytes IS NULL OR p_size_bytes < 1
     OR p_manifest_sha256 IS NULL OR p_manifest_sha256 !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'invalid resume checkpoint metadata';
  END IF;

  UPDATE training_api.training_status
  SET last_checkpoint_id = p_checkpoint_id,
      last_checkpoint_step = p_step,
      last_checkpoint_at = v_now,
      last_checkpoint_size_bytes = p_size_bytes,
      last_checkpoint_verified = true,
      last_checkpoint_manifest_sha256 = p_manifest_sha256,
      current_step = p_step,
      current_topic = p_current_topic,
      difficulty = greatest(1, p_difficulty),
      data_position = greatest(0, p_data_position),
      data_epoch = greatest(0, p_data_epoch),
      loss = p_loss,
      learning_rate = p_learning_rate,
      accuracy_by_topic = coalesce(p_accuracy_by_topic, '{}'::jsonb),
      curriculum_state = coalesce(p_curriculum_state, '{}'::jsonb),
      requested_resume_checkpoint_id = NULL,
      last_heartbeat_at = v_now,
      last_error = NULL,
      updated_at = v_now
  WHERE run_id = p_run_id
    AND owner_id = p_owner_id
    AND lease_holder = p_worker_id
    AND fencing_token = p_fencing_token
    AND lease_expires_at > v_now
    AND requested_resume_checkpoint_id = p_checkpoint_id
  RETURNING * INTO v_row;

  IF NOT FOUND THEN
    RETURN pg_catalog.jsonb_build_object('ok', false, 'reason', 'resume_request_or_lease_mismatch');
  END IF;

  RETURN pg_catalog.jsonb_build_object('ok', true, 'checkpoint_id', v_row.last_checkpoint_id, 'step', v_row.last_checkpoint_step);
END;
$ultron$;

CREATE OR REPLACE FUNCTION training_api.clear_resume_checkpoint_request(
  p_run_id uuid,
  p_owner_id uuid,
  p_worker_id text,
  p_fencing_token bigint,
  p_requested_checkpoint_id text,
  p_reason text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $ultron$
DECLARE
  v_updated integer;
BEGIN
  UPDATE training_api.training_status
  SET requested_resume_checkpoint_id = NULL,
      last_error = left(coalesce(p_reason, 'Requested checkpoint was unavailable; using the latest verified checkpoint.'), 500),
      updated_at = pg_catalog.clock_timestamp()
  WHERE run_id = p_run_id
    AND owner_id = p_owner_id
    AND lease_holder = p_worker_id
    AND fencing_token = p_fencing_token
    AND lease_expires_at > pg_catalog.clock_timestamp()
    AND requested_resume_checkpoint_id = p_requested_checkpoint_id;

  GET DIAGNOSTICS v_updated = ROW_COUNT;
  RETURN pg_catalog.jsonb_build_object('ok', v_updated = 1);
END;
$ultron$;

REVOKE ALL ON FUNCTION training_api.select_resume_checkpoint(uuid, uuid, text, bigint, text, bigint, bigint, text, text, smallint, bigint, bigint, double precision, double precision, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION training_api.clear_resume_checkpoint_request(uuid, uuid, text, bigint, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION training_api.select_resume_checkpoint(uuid, uuid, text, bigint, text, bigint, bigint, text, text, smallint, bigint, bigint, double precision, double precision, jsonb, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION training_api.clear_resume_checkpoint_request(uuid, uuid, text, bigint, text, text) TO service_role;

NOTIFY pgrst, 'reload schema';
