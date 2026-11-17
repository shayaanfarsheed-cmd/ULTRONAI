# ULTRON Online Dashboard + Windows Local Training Agent

Status: Stage 1 architecture specification. No local agent has been implemented and no training has started.

## Hosting and runtime boundaries

- GitHub Pages hosts the static dashboard at https://shayaanfarsheed-cmd.github.io/ULTRONAI/.
- Supabase provides user authentication, durable control state, device registration, command records, status/heartbeat records, and checkpoint coordination.
- Windows local agent runs on the user's Windows computer and makes outbound HTTPS requests only. No public inbound port, router port-forward, or remote shell is required.
- ULTRON training process runs locally as a child process started only by the agent after local validation.
- iPad and other browsers access the same GitHub Pages dashboard and control the registered Windows agent over Supabase.

GitHub Pages is static hosting. It cannot execute Python, hold private server credentials, or directly start a process on Windows.

## Command flow

1. The user signs in to the dashboard using Supabase Auth.
2. The user explicitly pairs a Windows agent with the account.
3. The dashboard requests a narrowly-scoped action through a Supabase Edge Function.
4. The function verifies the user's JWT, device ownership, command allowlist, current state, and one-active-run policy before writing a command.
5. The Windows agent polls the Edge Function over outbound HTTPS using its own revocable device credential.
6. The agent validates command ID, expiry, nonce/idempotency, allowed action and local safety state. It does not interpret or execute arbitrary shell text.
7. For start, the agent launches only the fixed project entry point with a fixed argument schema. It records PID/process identity and reports status.
8. The agent sends heartbeats and bounded telemetry. Pause/resume/stop are cooperative commands handled by the training process.
9. Training checkpoints remain local first and are synchronized to the existing Supabase checkpoint system when configured. The existing one-writer lease and fencing-token checks remain mandatory.

## Security model

- Never expose Supabase sb_secret / service-role credentials in GitHub Pages, browser JavaScript, notebook output, or the agent's ordinary config file.
- The browser uses only the Supabase publishable/anon key and a signed-in user's JWT.
- Device pairing should issue a random per-device credential once. Store only its hash server-side; store the credential in Windows Credential Manager (or an equivalent OS-protected secret store), not in source code or a plaintext committed file.
- Edge Functions validate the device credential, owner, device status, command expiry and idempotency. Revoke a device by disabling its registration and rotating its credential.
- Commands are an enum (start, pause, resume, stop, status) with validated JSON parameters, including a bounded `memory_limit_gb` on start. No shell command, PowerShell, Python snippet, URL, or arbitrary executable path is accepted from the dashboard.
- Start is disabled until local preflight passes, the model/data/config paths resolve inside the project directory, resource limits are applied, and no other ULTRON trainer is active.
- The agent binds any optional local diagnostics endpoint to loopback only. Remote browser control goes through outbound HTTPS polling, not an exposed local web server.
- Require explicit confirmation for first start and destructive actions. Stop is cooperative; hard termination is a separately guarded recovery action.
- A command is acknowledged once and is idempotent. Expired, replayed, unknown, or out-of-order commands are rejected.
- The agent stops training if it loses the authoritative Supabase lease or cannot safely renew it before the configured deadline. A secondary checkpoint is not permission to continue without a valid lease.
- No automatic cloud-server switching in this stage. Future providers must use the same one-writer lease and free-tier-only policy.

## Local training memory limit

- Dashboard setting: `memory_limit_gb`, numeric range 2.0–10.0 GB in 0.5 GB increments; initial default 6.0 GB for the user's 16 GB laptop.
- The dashboard preference is currently browser-local only. It is not considered applied until a paired Windows agent acknowledges the exact setting.
- The future command/API contract must validate the value server-side and include it in the signed/authorized start configuration; never accept arbitrary resource-control arguments.
- Before launch, the Windows agent must check physical RAM and reserve at least 6 GB for Windows and other applications. If the selected cap exceeds total RAM minus the reserve, reject the start and report the safe maximum.
- Enforce the cap on the entire training process tree with a Windows Job Object memory limit. Create the child suspended, assign it to the Job Object, then resume it so child workers inherit the job. Do not rely on a Python-side estimate or dashboard display as enforcement.
- Report configured cap and observed process/job memory in agent telemetry. Stop safely on memory-limit failure and preserve the last verified checkpoint.
- This is system RAM, not GPU VRAM. GPU memory remains governed by the training runtime's batch-size/device checks.

## Initial command contract

| Action | Required checks | Result |
|---|---|---|
| status | Device paired and active | Return bounded status/telemetry |
| start | User confirmation, preflight passed, no active process, valid lease | Start fixed train.py entry point |
| pause | Matching active run | Request checkpointed pause |
| resume | Paused run, verified checkpoint, valid lease | Resume from verified checkpoint |
| stop | Matching active run | Request graceful checkpoint and stop |

No command accepts arbitrary command-line text or code.

## Stage plan

1. Architecture and security contract — this document; inspect current repository and identify integration boundaries.
2. Backend contract — migration for paired devices and command records, RLS policies, and Edge Functions. Add tests for owner isolation, expired/replayed commands, and credential revocation.
3. Windows agent skeleton — install/run instructions, secure credential storage, outbound polling, command allowlist, local status, and safe shutdown. No training start until tests pass.
4. Training adapter — fixed launch contract for the existing train.py, preflight checks, process supervision, one-writer lease enforcement and checkpointed pause/stop.
5. GitHub Pages dashboard — device pairing UI, online/offline state, Run/Pause/Resume/Stop controls, audit log and telemetry. Controls remain disabled unless a healthy paired agent is online.
6. Verification — automated tests, Windows local smoke test, browser/iPad test, security review and recovery tests. Only then enable real training.
7. Later — free cloud providers and sequential handoff after the local workflow is proven.

## Current repository findings

- The repository already contains a static dashboard under dashboard/ and README instructions for GitHub Pages.
- The current dashboard is designed around notebook/server rotation and Supabase training status. It does not yet pair with a Windows agent or implement a local RUN command.
- dashboard/config.js still contains the public-key placeholder. The dashboard is not ready for live sign-in until the user configures it.
- GitHub Pages still needs to be enabled in repository Settings.
- Existing Supabase training tables and checkpoint coordination should be reviewed before adding new objects. Do not change existing public memory tables or weaken the current RLS/lease policies.
- The current project must retain: from-scratch model, no pretrained weights, no AI APIs, generated and independently verified math data, free-only compute, one active trainer, and resumable verified checkpoints.

## Stage 1 acceptance

- Hosting choice recorded as GitHub Pages.
- Static dashboard, current config placeholder, Supabase setup instructions and existing control scope inspected.
- Local agent trust boundary and command allowlist specified.
- No secret values added to source.
- No training started.

## Stage 2 read-only backend inspection (2026-11-17)

The connected Supabase project `ultron-memory` (`euhmejpaswmdpsutbtse`) is reachable and reports `ACTIVE_HEALTHY` on PostgreSQL 17.12. This inspection made no database changes.

### Existing objects and controls

- The exposed training backend schema is `training_api`.
- Existing tables are `training_status`, `server_log`, and `switch_requests`; all three have RLS enabled.
- The existing RLS policies restrict dashboard reads and permitted updates/inserts to `owner_id = auth.uid()`. The dashboard is deliberately granted only selected control-column updates on `training_status`.
- Existing lease/checkpoint RPC functions use `SECURITY INVOKER` and are granted to `service_role` only. Preserve this model; do not grant device agents broad table access.
- Six existing public memory tables are present and have owner-scoped RLS. Do not modify them.
- Four database migrations are recorded: `secure_ultron_memory_rls`, `ultron_training_control_schema`, `ultron_checkpoint_commit_step`, and `ultron_handoff_request_flag`.
- No Supabase Edge Functions currently exist.
- The Supabase Security Advisor returned no findings at inspection time.

### Implications for the local-agent backend

Do not add agent command writes to the existing dashboard-writable training tables. The next backend proposal should add a separate, narrowly scoped control plane in the non-exposed `training_api` schema (or a dedicated private schema after confirming grants), with:
- device registration records containing owner, public device metadata, credential hash, created/last-seen/revoked timestamps, and status;
- short-lived, single-use pairing challenges, stored hashed and consumed atomically;
- command records with a strict enum (`start`, `pause`, `resume`, `stop`, `status`), validated bounded payload, owner/device IDs, creation/expiry, idempotency key, claim/ack timestamps, and result;
- RPC or Edge Function operations that atomically validate owner/device, credential, expiry, replay, active-run policy and state transitions;
- agent polling and acknowledgement authenticated with a revocable per-device credential, separate from the user's browser JWT;
- no direct browser access to device credentials or command queue tables.

The current schema does not contain device or command tables, and no Edge Functions are deployed. Do not create them until the SQL/RLS/function contract and test cases have been reviewed. The RAM slider remains browser-local until a paired agent confirms the applied cap; the future `start` command must include the validated `memory_limit_gb` (2.0–10.0, 0.5 increments), and the Windows agent must enforce it using a Job Object before resuming the training process.

### Current stage result

Stage 2 discovery is complete; implementation has not begun. No Supabase tables, policies, functions, secrets, or existing training data were changed. Next: prepare the proposed schema and Edge Function contract plus negative security tests for review, then implement only after the design is approved.
