# ULTRON — Browser Dashboard and Device-Agent Architecture

**Status:** target architecture and safety contract. Owner authentication, device registry, pairing endpoints and agents are not implemented. No training has started.

## Product access model

- The website is hosted as a static GitHub Pages application and must work on iPad, phone, tablet and desktop browsers.
- Guest Mode is public and requires no account. It exposes public dashboard and public mathematics information only.
- One restricted owner account provides access to private dashboard features after secure authentication is implemented.
- Public self-registration is disabled. There is one intended owner identity, not a public multi-user signup system.
- Guests cannot view private training history/checkpoints, pair devices, or issue remote training controls.
- Hiding a control in JavaScript is not authorization. Every private operation must be authorized by a trusted backend using a verified owner session.
- The owner ID is derived server-side. Never trust a client-supplied owner ID.

**Current implementation truth:** the dashboard is currently public-mode only. Owner login, logout, password recovery, owner-only provisioning and private backend authorization are not yet implemented. Keep privileged controls locked.

## Hosting and runtime boundaries

- GitHub Pages hosts the static website.
- Supabase is the planned authentication and coordination backend, subject to separate approval for production changes.
- GitHub Pages cannot execute Python, hold private server credentials, or start a local process.
- Training runs only on a compatible worker/agent, never inside GitHub Pages.
- The user may operate the website from an iPad; iPadOS and mobile browsers are control/monitoring clients by default, not assumed training workers.

## Device capability model

A paired agent must report measured metadata: operating system, architecture, agent version, available memory, CPU, accelerator/runtime availability and training state. Unknown values remain unknown; never invent capabilities.

A device can be paired but still be ineligible to train. Capability preflight, resource enforcement, checkpoint validation and the authoritative lease are all required before launch.

## Command flow — future implementation

1. The owner authenticates through the restricted owner account. A guest cannot enter this flow.
2. The owner requests a one-time, short-lived pairing challenge through a trusted backend endpoint.
3. The agent redeems the challenge once and receives a unique revocable device credential.
4. The agent stores its credential in the operating system's protected credential store; the backend stores only a digest.
5. Owner command requests pass through a narrow trusted endpoint that verifies the owner session, device ownership, device state and action allowlist.
6. The agent polls over outbound HTTPS and authenticates as the device, not as the owner.
7. The agent validates command ID, expiry, nonce/idempotency, allowed action and local safety state. It never executes arbitrary shell text.
8. For a start request, the agent launches only the fixed ULTRON training entry point after platform, memory, path, checkpoint and lease checks.
9. Heartbeats and telemetry are bounded and redacted.
10. The worker uses the existing single-writer lease and fencing-token rules for all durable training/checkpoint operations.

Exactly-once execution cannot be guaranteed across process crashes and lost acknowledgements. Use idempotency and reconciliation; never blindly re-run a command whose execution may have started.

## Security model

- Never expose Supabase secret/service-role credentials in GitHub Pages, browser JavaScript, notebook output or ordinary agent configuration.
- A publishable key is public and is not owner authentication.
- Owner authorization and device authentication are separate trust domains.
- Pairing codes are high entropy, single-use, short-lived (maximum 10 minutes), rate-limited and stored server-side as digests.
- Device credentials are unique, revocable, rotatable and stored in an OS-protected credential store.
- Commands are an enum (start, pause, resume, stop, status) with action-specific validated parameters. No shell, PowerShell, Python snippet, arbitrary URL or executable path is accepted.
- Revocation denies subsequent device requests and causes active work to fail closed.
- The existing training lease/fencing mechanism remains the only authoritative single-writer lease.
- A stale worker cannot commit a checkpoint or perform durable side effects.
- Audit logs contain bounded redacted metadata, never secrets or arbitrary command output.

## Platform and resource enforcement

The RAM slider is currently a browser-local preference. It does not constrain a browser tab, another device, or an external process.

| Platform | Intended role | Enforcement requirement |
|---|---|---|
| Windows | Potential desktop worker | Windows Job Objects; assign the process before it executes and contain descendants |
| Linux | Potential desktop/cloud worker | cgroups v2 or verified systemd scope |
| macOS | Potential desktop worker | Remains ineligible until a strict enforceable cap is implemented and tested |
| iPadOS / iOS | Dashboard client | Monitoring/control only by default; no native training claim |
| Android | Dashboard client | Monitoring/control only by default; no native training claim |
| Browser-only | Dashboard client | Browser preference only; cannot enforce an external worker's RAM |

The agent must refuse training if the selected platform cannot prove an enforceable memory cap. Tests must attempt to exceed the cap and verify that the operating system stops/contains the workload. A UI slider changing value is not proof of enforcement.

## Initial command contract

| Action | Required checks | Result |
|---|---|---|
| status | Active paired device and valid device credential | Bounded status/telemetry |
| start | Verified owner request, capability preflight, enforced memory cap, no active process, valid lease | Start fixed training entry point |
| pause | Matching active run and current lease | Request checkpointed pause |
| resume | Paused run, verified checkpoint and valid lease | Resume verified checkpoint |
| stop | Matching active run | Graceful bounded shutdown |

No command accepts arbitrary command-line text or code.

## Existing backend boundary

The repository documents a `training_api` schema with `training_status`, `server_log` and `switch_requests`, owner-scoped policies, lease/checkpoint RPCs and private checkpoint storage. These repository statements are not a fresh live Supabase verification.

No device registry, pairing challenge table, device credential registry, device command queue or device-control Edge Function existed in the reviewed source. Do not write device commands into the existing dashboard-writable training tables. Propose a separate non-public control plane and review its grants, RLS, transaction semantics and negative authorization tests before any deployment.

## Required verification

- Guest cannot read or mutate private rows, RPCs, checkpoints, device records or commands.
- Owner A cannot access owner B's records by changing identifiers.
- Agent A cannot poll, claim or acknowledge for device B.
- Pairing challenge redemption is atomic and single-use.
- Duplicate command delivery cannot cause duplicate process launch.
- Revocation and stale fencing fail closed.
- Claim/execute/ack crash recovery never blindly replays uncertain work.
- Memory enforcement and descendant process termination are proven on each eligible OS.
- Lease loss stops work before the last known safe deadline.
- Checkpoint writes are atomic, integrity-checked and fenced.

## Approval gates

Separate explicit approval is required before any Supabase migration, RLS/grant change, Edge Function deployment, production secret change, owner-account provisioning, device pairing, agent installation, live training, provider job or PR merge. The permanent budget is $0; no paid tier, billing, payment method, paid trial or quota bypass is allowed.
