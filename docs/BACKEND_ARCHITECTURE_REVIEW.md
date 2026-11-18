# ULTRON Backend Architecture Review

**Status:** Stage 3 design review only — no migrations, database writes, RLS/grant changes, Edge Functions, secrets, pairing, or training were performed.

**Reviewed against:** `main` at `397f1492c300371821b2651ddfbc7342adc9f60c`, PR #4 head `fc1cfd0eaaa4424f66ea2368779510aa33845294` (18 November 2026).

## 1. Executive decision

Do not add device records or commands to the existing `training_api.training_status`, `server_log`, or `switch_requests` tables. Keep the device-control plane separate and server-mediated.

The existing training backend already has an owner-scoped run model, lease and fencing RPCs, checkpoint metadata, private checkpoint storage, and a Python REST client. Reuse its single-writer invariants through a narrow integration boundary; do not create a second independent training lease.

**Implementation is not approved by this review.** Stage 3 produces a proposal and test requirements only. Any Supabase migration, policy/grant change, Edge Function deployment, production secret change, pairing, live training, or PR merge requires its own explicit approval.

## 2. Repository facts and existing boundaries

Reviewed files:
- `supabase/schema.sql`
- `supabase/lease-functions.sql`
- `supabase/storage-setup.sql`
- `supabase/storage-policy.sql`
- `supabase/SETUP.md`
- `ultron_supabase.py` and `tests/test_supabase.py`
- `docs/LOCAL_AGENT_ARCHITECTURE.md`
- PR #4 device-control contract and threat model.

Current architecture:
- `training_api` contains `training_status`, `server_log`, and `switch_requests`.
- The existing tables have RLS enabled and owner-scoped authenticated-user policies.
- Authenticated users can read their own rows and update a narrow set of control columns; service_role has backend access.
- Lease/checkpoint operations are implemented as SECURITY INVOKER PostgreSQL RPCs, with server-side checks for owner, worker, lease expiry and fencing token.
- Checkpoints use a private `checkpoints` Storage bucket with owner-folder read policy.
- There is no device registry, pairing challenge table, device credential registry, device command queue, or device-control Edge Function in the inspected repository.
- Existing lease RPCs accept `p_owner_id`; a trusted caller must derive that owner from verified identity/context, never trust a browser-supplied owner ID.
- GitHub Pages is static hosting and cannot hold service credentials or launch a local process.

The existing SQL is not a complete device-control backend. In particular, training-worker lease RPCs do not provide device identity, pairing, device credential verification, command claim/ack, or device revocation.

## 3. Blocking product/security contradiction

The product requirement is a public dashboard with no login or sign-up. Existing `supabase/SETUP.md` and `docs/LOCAL_AGENT_ARCHITECTURE.md` still describe Supabase Auth sign-in, account creation and owner-specific dashboard control.

These cannot both be true for owner-specific privileged controls:
- Anonymous public users cannot securely establish which owner may pair, list, command, or revoke a device.
- A publishable Supabase key is public and is not an authorization credential.
- A device credential authenticates the agent, not the human owner issuing a browser command.

**Recommended safe interim decision:** keep the public site anonymous and informational; keep pairing, device listing, owner-specific commands, and privileged training controls disabled. Do not add login UI or weaken owner isolation. A future owner-authorization model must be explicitly chosen and approved before implementation. Possibilities requiring product decision include a separate owner-only control surface or a carefully scoped owner authorization mechanism; neither is selected or deployed by this document.

## 4. Proposed logical separation

Use a dedicated, non-public schema such as `device_control` (name provisional) for control-plane records. Do not expose it through the browser Data API. The browser must never call device tables directly.

Logical records:

| Record | Essential fields and constraints |
|---|---|
| devices | id, owner_id, status, credential_digest, credential_version, created_at, last_seen_at, revoked_at; unique device identity; never store plaintext credential |
| pairing_challenges | id, owner_id, secret_digest, expires_at, redeemed_at, revoked_at, attempt_count; single-use; short expiry; unique digest |
| device_commands | id, device_id, owner_id, action, strict parameters, status, issued_at, expires_at, nonce, claim_id, claim_expires_at, fencing_token, result_code, completed_at; unique (device_id, nonce) |
| device_audit_events | append-only event ID, device/owner IDs, actor type, event type, timestamp, bounded redacted metadata; no credentials or arbitrary logs |

Use foreign keys that preserve ownership consistency, including composite uniqueness/foreign keys where needed so a command's owner cannot differ from its device's owner. Use CHECK constraints for enums, bounds and state invariants. Add indexes for active device lookup, unexpired challenge lookup, per-device pending command claims, and audit chronology. Avoid storing unbounded JSON or arbitrary agent output.

The exact schema and index definitions must be validated against the selected PostgreSQL/Supabase version before migration design is finalized.

## 5. Authorization and privilege model

### Browser / public website
- Anonymous access: public static content only.
- No direct grants to `anon` on device-control tables or RPCs.
- No service_role, secret key, device credential, pairing secret, or backend pepper in browser code.
- Do not infer authorization from a hidden button, client-side owner ID, URL parameter, or publishable key.

### Owner-authorized control requests
- A trusted Edge Function must validate the chosen owner authorization mechanism.
- Derive `owner_id` from the verified identity/session on the server. Ignore/reject owner IDs supplied by the browser.
- Check device ownership and active status for every operation.
- Enforce action-specific state transitions, rate limits, request size limits and audit events.
- Return only bounded, non-sensitive results.
- Until owner authorization is resolved and approved, do not implement these endpoints.

### Device-agent requests
- Each device has an independent high-entropy random credential, shown once and stored in the OS credential store.
- Persist only a keyed digest (pepper held in a secret manager); compare safely and support immediate revocation and rotation.
- Agent requests use outbound HTTPS and authenticate as the device, not as an owner.
- A verified device identity is mapped to its owner by the server; the agent cannot choose its owner.
- Device endpoints expose only narrowly scoped poll/claim, heartbeat, acknowledge and status operations.

### Database
- Keep device-control schema unexposed to PostgREST where practical; only trusted backend code reaches it.
- Revoke default PUBLIC/anon/authenticated privileges explicitly.
- Prefer narrowly scoped database roles and RPC execution grants. If the Supabase service_role is used by an Edge Function, treat it as fully privileged and keep the function surface minimal; RLS does not constrain service_role bypass.
- Any SECURITY DEFINER function must use a fixed empty search_path, fully qualified object names, strict input validation, explicit EXECUTE revokes/grants, and adversarial tests. Prefer SECURITY INVOKER when it can meet the requirement.
- Do not assume a private schema alone provides authorization.

## 6. Atomic command lifecycle

Proposed state machine:

`pending -> claimed -> executing -> succeeded | failed`

Additional terminal paths: `pending -> expired | revoked`; a claim may return to pending only after claim expiry and verified proof that execution never began.

Required transaction semantics:
1. Validate device credential and active device status in the trusted server layer.
2. Claim one eligible command for that device in one database transaction, using row locking (e.g. `FOR UPDATE SKIP LOCKED`), a claim UUID and a short claim lease.
3. Enforce a partial unique constraint or equivalent invariant allowing at most one active claimed/executing command per device.
4. Persist transition to executing before invoking the fixed local action.
5. Acknowledge with command ID, claim ID and bounded result code; make duplicate acknowledgements idempotent.
6. Once executing, never blindly requeue after timeout or agent crash. Reconcile against a durable local execution journal and the known ULTRON process/run identity.
7. Persist every transition and actor in an audit trail without secrets.

Exactly-once execution cannot be guaranteed across process crashes and lost acknowledgements. Design for idempotency and reconciliation.

## 7. Command validity and replay controls

- Server/database time is authoritative for issued_at and expires_at.
- Enforce a maximum TTL of 120 seconds and documented clock-skew policy.
- Enforce a unique per-device nonce in persistent storage; an in-memory agent cache is not replay protection.
- Bind command, device, owner, claim and current fencing generation.
- Enforce strict action-specific parameter allowlists and maximum request/result sizes.
- Reject unknown fields, invalid UUIDs/timestamps, expired/future-dated commands, revoked devices, duplicate nonces and stale fencing tokens.
- Status results should use enumerated codes and a 4 KiB maximum payload; no arbitrary logs, secrets, shell output or user-provided executable text.

## 8. Lease and checkpoint integration

There must remain exactly one authoritative training writer across local devices and cloud providers.

- Device command issuance does not grant a training lease.
- A `start` command may request a start; the agent must independently pass platform, process, RAM-enforcement, checkpoint and lease preflight.
- The worker obtains the existing training lease and monotonic fencing token through the existing trusted lease path.
- Before every checkpoint commit and other durable side effect, the backend validates the current owner, worker, unexpired lease and exact fencing token.
- A stale worker must be rejected even if its local process still runs.
- The device-control layer must not mint, cache-authorize, or independently extend training leases.
- On uncertainty or inability to renew, stop safely; preserve a verified local checkpoint without claiming remote commit.

## 9. Storage and credential lifecycle

- Keep the existing checkpoint bucket private.
- Device-control credentials must not be stored in checkpoint objects, logs, command results, notebook output or GitHub files.
- Pairing secrets: high entropy, short-lived (maximum 10 minutes), one-time atomic redemption, hash-only storage, attempt limits and redacted audit.
- Device credentials: unique per device, revocable, rotatable, versioned, digest-only server storage, OS-protected agent storage.
- Revocation must immediately deny polling, claim, heartbeat, acknowledgement and new training start; active process shutdown is coordinated through fail-stop behavior.
- Checkpoint object paths must be owner-scoped and validated server-side; do not trust caller-provided object paths or checkpoint IDs.

## 10. Edge Function/API boundary

No Edge Functions currently exist in the inspected repository. If separately approved, keep the initial surface minimal:

| Endpoint concept | Caller | Required behavior |
|---|---|---|
| owner command request | approved owner control surface | verify owner authorization, device ownership, state and action; enqueue atomically |
| device poll/claim | paired agent | authenticate device credential; claim one command atomically |
| device heartbeat | paired agent | authenticate active device; bounded liveness metadata only |
| command acknowledgement | paired agent | authenticate device; verify claim/command binding; idempotent bounded result |
| revoke device | approved owner control surface | verify owner; revoke credential and device atomically |

Do not expose a generic SQL/RPC proxy, arbitrary function name, arbitrary URL, shell command, or user-supplied executable path. Apply per-device and per-owner rate limits, request body limits, structured redaction, and generic external error messages. Keep detailed diagnostics server-side without secrets.

## 11. Required verification before implementation approval

### Database authorization
- Anonymous role cannot select/insert/update/delete device records or execute device RPCs.
- Authenticated owner A cannot read, pair, command or revoke owner B's devices by changing IDs.
- Agent A cannot poll, claim, heartbeat or acknowledge for device B.
- Browser-supplied owner_id is ignored/rejected.
- Service-role access is limited to trusted server functions; verify grants and default privileges.

### Concurrency and recovery
- Two simultaneous pairing redemptions: exactly one succeeds.
- Two pollers racing for one command: exactly one claim succeeds.
- Claim expiry before execution can safely recover.
- Crash after EXECUTING does not requeue blindly.
- Duplicate acknowledgement is idempotent.
- Revocation races with polling/claim/ack fail closed.
- Lease takeover invalidates all old fencing tokens.
- Stale worker checkpoint commits and side effects are rejected.

### Input and abuse
- Expired/future commands, excessive TTL, duplicate nonce, malformed UUID/time, unknown action/fields, oversized body/result and secret-bearing result are rejected.
- Per-device and per-owner rate limits are tested.
- Logs and error responses contain no plaintext credentials, tokens, pairing secrets or pepper.

### Operational
- Edge Function auth and database transaction behavior tested locally with disposable fixtures.
- Failure injection covers database/network outage, process crash, duplicate delivery, clock skew, credential rotation and revocation.
- OS RAM enforcement and descendant process termination are independently proven before start is enabled.
- Free-tier quotas and limits are checked; no paid dependency, billing, or paid trial.

## 12. Stage 3 conclusion and next gate

**Architecture recommendation:** keep the existing training lease/checkpoint backend intact; design a separate private device-control schema and a small Edge Function boundary; preserve anonymous public-site behavior by leaving owner-specific controls disabled until an owner-authorization product decision is approved.

**Not performed:** no Supabase connection or live project inspection, no schema migration, no RLS/grant change, no Edge Function, no production secret change, no pairing, no device agent, no training, no paid service, and no PR merge.

**Next task:** resolve the public-dashboard versus owner-authentication requirement, then prepare a migration-by-migration implementation proposal and executable authorization/concurrency tests for review. Request explicit approval before any Supabase change.
