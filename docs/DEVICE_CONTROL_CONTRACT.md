# ULTRON Device Control Plane Contract

Status: proposal only. This document defines the first backend contract for review. It does not create tables, deploy functions, change Supabase policies, pair a device, or start training.

## Scope

The control plane connects the static GitHub Pages dashboard to desktop agents on Windows, macOS and Linux. The dashboard remains usable from iPad, iPhone and Android browsers. Mobile devices are control/monitoring clients by default, not training workers.

The first implementation must use Supabase Auth for the human user and narrowly scoped Edge Functions for privileged operations. No browser or agent receives a Supabase service-role/secret key.

## Proposed private data model

All tables belong in a non-exposed schema (proposed: `device_control`). Do not add these objects to the existing exposed `training_api` schema or reuse its dashboard-writable tables.

### `devices`

- `id`: UUID primary key.
- `owner_id`: UUID, references the authenticated owner.
- `display_name`: bounded plain text, length 1–80.
- `platform`: enum: `windows`, `macos`, `linux`.
- `architecture`: bounded value such as `x86_64` or `arm64`.
- `agent_version`: semantic version string.
- `credential_hash`: hash of a high-entropy random device credential; never return it after pairing.
- `status`: `pending`, `online`, `offline`, `revoked`.
- `last_seen_at`, `created_at`, `revoked_at`: server timestamps.

### `pairing_challenges`

- `id`: UUID primary key; `owner_id`: authenticated owner.
- `challenge_hash`: hash of a cryptographically random, one-time pairing secret.
- `expires_at`: short expiry (maximum 10 minutes).
- `consumed_at`: nullable; set atomically on successful pairing.
- Store no plaintext pairing secret. Pairing must be single-use and race-safe.

### `commands`

- `id`: UUID primary key; `device_id` and `owner_id`.
- `action`: enum: `status`, `start`, `pause`, `resume`, `stop`.
- `parameters`: validated JSON matching `schemas/device-command.schema.json`.
- `issued_at`, `expires_at`, `claimed_at`, `completed_at`.
- `nonce`: unique random idempotency value.
- `fencing_token`: lease generation required for run-affecting actions.
- `result_code`: bounded enum; do not store arbitrary agent logs in this field.

### `device_heartbeats`

- `device_id`, `observed_at`, `agent_version`, `platform`, `architecture`.
- Bounded capability fields: available memory, CPU count, training state, and enforcement support.
- Telemetry is untrusted agent input: validate types and ranges, cap payload size, and never treat a self-reported capability as proof that resource enforcement works.

## Authorization boundaries

1. Dashboard requests require a valid Supabase user JWT. The Edge Function derives `owner_id` from that JWT; it never trusts an owner ID supplied in request JSON.
2. A user may view and control only devices whose `owner_id` matches the JWT subject.
3. Device polling requires a per-device high-entropy credential. Store only a one-way credential hash server-side and compare in constant time.
4. The device credential can claim only commands for its own device. It cannot list devices, create pairing challenges, or access another device.
5. Pairing, command creation, credential rotation and revocation are server-side operations. No direct browser table writes.
6. Use rate limits for pairing attempts, polling, and command creation. Return generic authentication errors that do not disclose whether a device or challenge exists.
7. Revocation is immediate: reject future polls and command claims; the agent must stop any active run if its authenticated session is revoked or lease is lost.

## Pairing protocol

1. Signed-in dashboard calls `create-pairing-challenge`.
2. The function creates a cryptographically random secret, stores only its hash, and returns the secret once with an expiry no longer than 10 minutes.
3. The user transfers the one-time code to the desktop agent locally. Do not put it in a URL, analytics, logs, or support screenshots.
4. Agent exchanges the code over HTTPS. The server atomically consumes the challenge, creates a device row, and returns a new random device credential once.
5. Agent stores the credential in the operating system's protected secret store. The server stores only its hash.
6. Reuse, expiry, failed owner binding, or concurrent consumption must fail closed. Provide a dashboard revoke action.

## Agent polling and command execution

- Agent initiates outbound HTTPS polling; no inbound listener, port forwarding, remote desktop, or public local web server.
- Poll response contains at most one claimed command for that device.
- Every command has a UUID, nonce, short expiry, and a server-issued fencing token for run-affecting actions.
- Agent validates the command schema, device identity, expiry, nonce, current state, and lease before dispatch.
- The only executable actions are the fixed enum: `status`, `start`, `pause`, `resume`, `stop`.
- No arbitrary shell strings, PowerShell, Python snippets, executable paths, URLs, package installs, or user-supplied scripts are accepted.
- `start` launches only the repository's fixed ULTRON training entry point from a configured installation directory.
- Pause/resume/stop target the active run ID. Stop is graceful first; a bounded timeout may trigger termination of the owned process tree.
- Commands are idempotent. Re-delivery of a completed command returns the recorded result and never executes it twice.
- The agent acknowledges bounded result codes, not secrets or unbounded logs.

## Single-writer and resource safety

- All training workers, local and cloud, continue to use one authoritative lease and monotonically increasing fencing token.
- The agent must verify the current lease immediately before launch and periodically renew it.
- If lease renewal fails or the fencing token is superseded, the agent stops training and refuses new run commands.
- Memory preference is not enforcement. A start request is rejected unless the requested budget is within measured available memory and strict platform enforcement is confirmed.
- Windows uses a Job Object with the child assigned before execution. Linux uses cgroups v2 or a verified systemd scope. macOS remains training-ineligible until a strict, tested cap is available.
- A device may be paired and online while remaining training-ineligible.
- Mobile browsers do not advertise local compute capacity or enforce a desktop RAM limit.

## Required Edge Function surface

Proposed function names; no functions are deployed:

| Function | Caller | Responsibility |
|---|---|---|
| `create-pairing-challenge` | User JWT | Create one-time challenge |
| `complete-device-pairing` | Agent + challenge | Consume challenge, issue device credential |
| `list-my-devices` | User JWT | Return owner's safe device metadata |
| `revoke-device` | User JWT | Revoke owned device and credential |
| `create-device-command` | User JWT | Validate ownership, state, action and lease |
| `claim-device-command` | Device credential | Claim one unexpired command for that device |
| `ack-device-command` | Device credential | Acknowledge bounded result for that device |
| `post-device-heartbeat` | Device credential | Validate and record bounded telemetry |

Every function must validate method, content type, body size, authentication, authorization, input schema and rate limits. CORS is not an authorization mechanism.

## Security and acceptance tests before deployment

- A user cannot list, pair, command or revoke another user's device.
- Expired and replayed pairing challenges fail, including concurrent redemption.
- Plaintext device credentials never appear in database rows, logs, browser storage, or function responses after initial issuance.
- Revoked credentials cannot poll or acknowledge commands.
- An agent cannot claim another device's command.
- Unknown actions and extra command properties are rejected.
- Expired, duplicate, malformed and stale-fencing-token commands do not execute.
- A second worker cannot start while a valid lease exists.
- Losing the lease stops the worker before another training step is committed.
- A failed or unsupported memory-enforcement adapter refuses start.
- No arbitrary command text reaches a process API.
- Dashboard tests confirm controls remain disabled until a trusted backend and eligible agent are present.

## Approval gate

This contract is documentation only. Before any Supabase migration or Edge Function is created, review the proposed schema, exact RLS/grant model, function authentication flow, credential hashing/rotation strategy, and negative tests. Obtain explicit approval for those backend changes. Existing memory tables and policies remain untouched.
