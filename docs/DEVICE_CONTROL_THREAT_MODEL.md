# ULTRON Device Control Threat Model

**Status:** Stage 2 design review. This is a threat model and test plan only. It does not deploy a backend, create Supabase objects, pair devices, install an agent, or start training.

## 1. Security objectives

The future device-control system must preserve:

1. **Owner isolation:** one owner cannot enumerate, command, or revoke another owner's devices.
2. **Credential confidentiality:** pairing secrets and device credentials are short-lived or revocable, shown once, and never logged.
3. **Command integrity:** only allowlisted, schema-valid, unexpired commands reach the fixed ULTRON process controller.
4. **Single-writer training:** only the current lease holder and fencing-token generation can train or commit checkpoints.
5. **Fail-stop behaviour:** uncertainty about identity, lease ownership, command state, or memory enforcement prevents launch and stops active training.
6. **Resource containment:** the training process tree remains inside verified OS memory limits.
7. **Supply-chain integrity:** only verified agent releases and updates can execute.
8. **Zero-cost operation:** all implementation, testing, hosting, and training must stay within genuinely free services and the permanent $0 budget.
9. **Public-site privacy:** the public dashboard remains no-login/no-sign-up and exposes no owner-specific data or privileged controls.

## 2. Assets and security impact

| Asset | Security impact if compromised |
|---|---|
| Owner identity and device ownership records | Cross-owner takeover or privacy breach |
| Pairing challenge | Unauthorized device enrollment |
| Device credential and server-side digest pepper | Agent impersonation |
| Command queue and command nonce | Unauthorized/replayed actions |
| Lease and fencing token | Concurrent or stale training workers |
| Checkpoints and manifests | Lost, corrupted, or substituted training progress |
| Agent executable and update metadata | Arbitrary code execution on a training device |
| Local training process and model files | Data loss, resource exhaustion, process takeover |
| OS memory-enforcement configuration | Unbounded memory use or host instability |
| Provider secrets | Backend compromise and unexpected external access |

## 3. Actors and trust assumptions

### Actors

- **Anonymous visitor:** can load the public website and inspect public information. Must not gain owner or device privileges.
- **Future authenticated owner:** may manage only their own devices if an approved owner-authentication design is introduced.
- **Paired agent:** may poll and acknowledge commands for its own device only.
- **Cloud training worker:** competes for the same authoritative training lease; it is not trusted to override fencing.
- **Network attacker:** may observe, delay, replay, or modify traffic; HTTPS/TLS is required.
- **Compromised owner account:** may issue malicious but otherwise authorized commands; rate limits, audit trails, fixed command allowlists, and revocation reduce impact.
- **Local unprivileged user:** may attempt to replace files, steal credentials, alter configuration, or interfere with the process.
- **Compromised local administrator/root:** can generally control the host. The agent cannot fully defend against a malicious machine administrator; this is a documented residual risk.
- **Compromised backend/service role:** can bypass database RLS. Treat this as a critical incident requiring secret rotation, device credential revocation, and audit review.

### Trust assumptions

- HTTPS certificate validation is enabled; no insecure TLS bypass.
- Secrets are held only in provider secret managers or OS-protected credential stores.
- Agent releases are signed and signature verification keys are pinned through a trusted update channel.
- Server time and database transactions are authoritative for command issuance, claiming, expiry, ownership, and leases.
- A local cache is never the authority for current lease ownership or distributed replay protection.
- Public dashboard JavaScript and all browser input are untrusted.

## 4. Threat register

| ID | Threat / attacker capability | Required control | Verification |
|---|---|---|---|
| T-01 | Anonymous visitor calls hidden backend endpoints | No anonymous device endpoints; deny by default; no direct table grants | Anonymous request tests |
| T-02 | Owner changes owner_id in request body | Derive owner from verified identity; scope every query and mutation | Cross-owner negative tests |
| T-03 | Pairing code is photographed, copied, or intercepted | 256-bit random secret, <=10-minute expiry, hash-only storage, one-time atomic redemption | Expiry, replay, and concurrent redemption tests |
| T-04 | Attacker replays a device credential | TLS, per-device credential, revocation, rate limits, server-side credential verification | Replay and revocation tests |
| T-05 | Attacker replays a command | Unique per-device nonce, command ID, bounded expiry, durable execution journal | Duplicate and stale-command tests |
| T-06 | Two pollers claim the same command | Transactional row lock/claim lease and one active claim per device | Concurrent claim test |
| T-07 | Agent crashes after claim | Claim may expire back to pending only before execution starts | Crash-after-claim test |
| T-08 | Agent crashes after process launch but before acknowledgement | Durable executing journal and process/run reconciliation; never blindly requeue | Crash-after-launch test |
| T-09 | Old worker commits after lease takeover | Monotonic fencing token checked by server before every side effect | Stale-token checkpoint rejection |
| T-10 | Network/database outage hides lease loss | Fail closed; stop within 10 seconds; no offline lease extension | Heartbeat outage and shutdown test |
| T-11 | Malicious command attempts shell execution | Strict enum; no shell/script/path/URL fields; fixed entry point | Schema and process-boundary tests |
| T-12 | Agent reports false RAM capability | Server never trusts self-report; OS adapter must verify actual limits | Enforcement refusal tests |
| T-13 | Child process escapes memory/job limits | Assign before resume; contain descendants; verify process-tree membership | Descendant process test |
| T-14 | Malicious or downgraded agent update | Signed releases, version policy, rollback protection, verified updater | Tampered/unsigned update tests |
| T-15 | Local user edits agent config or binary | Protected install/config paths, signature checks, secure IPC | Tamper and permission tests |
| T-16 | Backend logs contain credentials | Structured redaction and bounded result codes | Log-secret scanning |
| T-17 | Result payload floods storage or exposes secrets | 4 KiB cap, enumerated result codes, no arbitrary logs | Oversize and secret-bearing payload tests |
| T-18 | Free provider quota ends during training | Frequent verified checkpoints, safe stop, provider switching only after lease handoff | Interrupted-session recovery test |

## 5. State machines

### 5.1 Pairing challenge

Allowed transitions:

- CREATED -> REDEEMED
- CREATED -> EXPIRED
- CREATED -> REVOKED

REDEEMED, EXPIRED, and REVOKED are terminal.

Rules:
- Only one transaction may change CREATED to REDEEMED.
- Concurrent redemptions must yield exactly one winner.
- A failed or expired attempt never returns the plaintext secret.
- A challenge cannot be reset to CREATED.
- Until an owner-authorization mechanism is explicitly approved, the public no-login dashboard cannot create or redeem owner-bound challenges.

### 5.2 Device

Allowed transitions:

- PENDING -> ONLINE
- ONLINE -> OFFLINE
- OFFLINE -> ONLINE
- PENDING/ONLINE/OFFLINE -> REVOKED

REVOKED is terminal. Re-enrollment requires a new pairing and new device identity/credential.

Rules:
- Revocation invalidates the credential immediately.
- A revoked device cannot poll, claim, acknowledge, heartbeat, or start training.
- Device status is not proof that the device is training-eligible.

### 5.3 Command

Allowed transitions:

- PENDING -> CLAIMED
- PENDING -> EXPIRED
- PENDING -> REVOKED
- CLAIMED -> EXECUTING
- CLAIMED -> PENDING only after claim timeout and verified proof that execution never began
- CLAIMED -> EXPIRED/REVOKED
- EXECUTING -> SUCCEEDED/FAILED/REVOKED

Rules:
- Claim is atomic and scoped to one device.
- Only one command may be CLAIMED or EXECUTING per device.
- Once EXECUTING, never automatically return the command to PENDING.
- After an execution crash, reconcile process identity and run state; if uncertain, stop and require safe recovery.
- A duplicate acknowledgement with identical terminal state is idempotent; a conflicting terminal result is rejected.
- Commands expire no later than 120 seconds after server issuance; accepted issue-time clock skew is at most 30 seconds.

### 5.4 Device credential

Allowed transitions:

- ISSUED -> ACTIVE
- ACTIVE -> ROTATED
- ACTIVE -> REVOKED
- ROTATED/REVOKED -> TERMINAL

Rules:
- Display plaintext once.
- Rotation atomically invalidates the old credential.
- No indefinite overlap.
- Lost OS credential store means revoke and pair again; do not recover plaintext from the server.

### 5.5 Training lease

Conceptual transitions:

- FREE -> HELD(token N)
- HELD(token N) -> RENEWED(token N) by the same valid holder
- HELD(token N) -> EXPIRED
- EXPIRED -> HELD(token N+1) by a new holder
- Any holder -> LOST when renewal/validation fails
- LOST -> STOPPING -> STOPPED

Rules:
- Token generation strictly increases on ownership change.
- A worker with token N cannot commit after token N+1 exists.
- Local memory must never extend server lease expiry.
- Lease loss or uncertainty stops training and blocks further checkpoints.
- Server-side writes re-check fencing independently of agent checks.

### 5.6 Process shutdown

Trigger: lease loss, credential revocation, command stop, heartbeat timeout, or enforcement failure.

1. Reject new start/resume commands.
2. Request graceful termination immediately.
3. Wait a bounded grace period.
4. Terminate the owned process tree.
5. Verify process exit and release local resources.
6. Mark local state stopped/lease-lost; do not claim a successful remote checkpoint unless the server confirms it.

Total shutdown target is at most 10 seconds. If the OS cannot confirm termination, report a critical local failure and keep the device ineligible.

## 6. Failure-injection test plan

| Test | Injection | Required outcome |
|---|---|---|
| F-01 | Two clients redeem one pairing challenge simultaneously | Exactly one succeeds |
| F-02 | Redeem expired or previously consumed challenge | Rejected; no device created |
| F-03 | Revoke credential while agent polls | Next request rejected; active run stops |
| F-04 | Submit another owner's device ID | No data disclosure or mutation |
| F-05 | Deliver same command twice | At most one execution |
| F-06 | Crash after claim but before execution journal | Claim can safely expire and be reclaimed |
| F-07 | Crash after execution journal/process launch | No blind re-execution; reconcile or stop |
| F-08 | Lose acknowledgement after successful execution | Retry acknowledgement is idempotent |
| F-09 | Send conflicting acknowledgement | Rejected and audited |
| F-10 | Let lease expire, then let old worker checkpoint | Server rejects stale token |
| F-11 | Simulate heartbeat outage near expiry | Local stop within 10 seconds; no remote commit/release |
| F-12 | Move local clock outside allowed skew | Command rejected |
| F-13 | Send command with TTL >120 seconds | Rejected |
| F-14 | Send arbitrary shell/script parameter | Schema and runtime reject it |
| F-15 | Disable Windows Job Object or Linux cgroups v2 | Start refused |
| F-16 | Spawn descendant process | Descendant remains contained and is terminated |
| F-17 | Replace agent binary/update package | Signature verification blocks execution |
| F-18 | Remove OS credential-store entry | Agent fails closed; requires re-pair |
| F-19 | Send oversized result or credential in result | Rejected and secret redacted |
| F-20 | Disconnect free compute provider | Checkpoint verified; worker stops; resume only after a new valid lease |

## 7. Residual risks and explicit non-goals

- A local administrator/root can generally tamper with the host or inspect process memory. Do not claim protection against a fully compromised host.
- A compromised backend service role can bypass RLS; rotate backend secrets and revoke all device credentials during incident response.
- Exactly-once execution across a process crash and lost network acknowledgement is not generally achievable. The system must use idempotency and reconciliation rather than claiming exactly-once guarantees.
- Free compute providers can revoke sessions, change quotas, or become unavailable. The system must checkpoint and stop safely, not bypass provider restrictions.
- This threat model does not authorize authentication UI, database deployment, production secrets, device pairing, agent installation, live training, paid services, or dashboard control unlocks.

## 8. Approval and next-stage gate

Before Stage 3 backend design is treated as implementation-ready, review:
- The owner-authorization design against the no-login public website requirement.
- Exact database grants, RLS, constraints, indexes, and transaction boundaries.
- Atomic claim/ack and recovery semantics.
- Credential issuance, storage, rotation, and revocation.
- Lease fencing and checkpoint commit rules.
- Agent release/update trust chain.
- Windows/Linux memory-enforcement proof and platform test strategy.
- All failure-injection tests and expected audit events.

Any Supabase migration, RLS/grant change, Edge Function deployment, production secret change, pairing, training, paid service, or PR merge remains behind its own explicit approval gate.
