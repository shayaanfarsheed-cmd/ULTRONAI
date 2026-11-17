# ULTRON Online Dashboard + Cross-Platform Device Agents

Status: Stage 1 architecture specification. Device agents and pairing are not implemented; no training has started.

## Hosting and runtime boundaries

- GitHub Pages hosts the static dashboard at https://shayaanfarsheed-cmd.github.io/ULTRONAI/.
- Supabase provides authentication and, after approval, the private device/control plane.
- The dashboard is browser-based and should work on desktop, iPad, iPhone and Android browsers.
- Training runs only on a compatible device agent, never inside GitHub Pages.
- Desktop adapters are planned for Windows, macOS and Linux. Mobile browsers are supported for monitoring/control; native mobile training is not promised and requires separate capability and platform validation.

GitHub Pages is static hosting. It cannot execute Python, hold private server credentials, or directly start a local process.

## Device capability model

A connected agent must report truthful, measured metadata: platform, architecture, agent/runtime version, available system memory, CPU characteristics, GPU/runtime availability and current training state. Unknown values remain unavailable rather than being guessed.

The backend and agent perform capability preflight before any training command. A device may pair successfully yet remain ineligible to train. iPadOS, iOS and Android devices can use the dashboard; they are not automatically training workers. One active training writer is permitted across all devices and providers.

The RAM slider is a browser-saved preference only. A future agent must validate it against actual available memory and enforce it using platform-specific process controls. If strict enforcement is not supported or verified on a platform, training must remain disabled there.

## Command flow

1. The user signs in to the dashboard using Supabase Auth.
2. The user explicitly pairs a device using a short-lived, single-use challenge.
3. The dashboard requests a narrowly scoped action through a Supabase Edge Function.
4. The function verifies the user's JWT, device ownership, command allowlist, current state and one-active-run policy.
5. The device agent polls over outbound HTTPS using its own revocable credential.
6. The agent validates command ID, expiry, nonce/idempotency, allowed action and local safety state. It never executes arbitrary shell text.
7. For start, the agent launches only the fixed ULTRON training entry point after capability, memory, path and lease checks.
8. The agent sends bounded heartbeats and telemetry. Pause/resume/stop are cooperative commands.
9. Verified checkpoints are committed and synchronized under the existing one-writer lease and fencing-token rules.

## Security model

- Never expose Supabase service-role credentials in GitHub Pages, browser JavaScript, notebook output or ordinary agent config.
- The browser uses only the publishable/anon key and signed-in user JWT.
- Pairing issues a random per-device credential once. Store only its hash server-side; store the credential in an OS-protected secret store.
- Edge Functions validate credential, owner, device status, command expiry and idempotency. Revocation disables the registration and invalidates the credential.
- Commands are an enum (start, pause, resume, stop, status) with validated JSON parameters. No shell command, PowerShell, Python snippet, URL or arbitrary executable path is accepted.
- Start requires local preflight, fixed project paths, enforced resource limits and a valid single-writer lease.
- The agent stops training if it loses the authoritative lease or cannot renew it before the deadline.
- No automatic cloud-server switching in this stage. Future providers must use the same one-writer lease and free-tier-only policy.

## Platform-specific enforcement requirements

- Windows: use Job Objects for process-tree memory limits; assign the child before allowing it to execute.
- Linux: use cgroups v2 or a verified systemd scope.
- macOS: implement and test an appropriate resource-control strategy; if a strict cap cannot be guaranteed, refuse training rather than claim enforcement.
- iPadOS/iOS/Android: dashboard-only by default. Any future native runtime requires a separate design, compatibility matrix and explicit tests.
- Browser-only devices: control surface only; never imply browser memory preferences constrain an external training process.

## Initial command contract

| Action | Required checks | Result |
|---|---|---|
| status | Device paired and active | Bounded status and telemetry |
| start | User confirmation, capability preflight, memory enforcement, no active process, valid lease | Start fixed training entry point |
| pause | Matching active run | Request checkpointed pause |
| resume | Paused run, verified checkpoint, valid lease | Resume verified checkpoint |
| stop | Matching active run | Request graceful checkpoint and stop |

No command accepts arbitrary command-line text or code.

## Stage plan

1. Architecture and security contract — inspect repository and integration boundaries.
2. Backend contract — propose private device registry, pairing challenges, command records, RLS and Edge Functions; review negative security tests before implementation.
3. Device agent skeletons — platform-specific adapters, secure credential storage, outbound polling, allowlisted commands and safe shutdown.
4. Training adapter — fixed launch contract, preflight, memory enforcement, lease enforcement and checkpointed pause/stop.
5. Dashboard integration — pairing, capability display, live status, controls and telemetry. Controls remain disabled unless a compatible authenticated agent is online.
6. Verification — automated tests, desktop OS smoke tests, iPad/mobile browser tests, security review and recovery tests.
7. Later — sequential free cloud providers after the local workflow is proven.

## Existing backend inspection

The Supabase project has an existing `training_api` schema with `training_status`, `server_log` and `switch_requests`; RLS is enabled and owner-scoped. Existing lease/checkpoint RPCs are SECURITY INVOKER and granted to service_role only. Six public memory tables have owner-scoped RLS. Four migrations exist; no Edge Functions or device registry/command queue currently exist. No database changes were made during inspection.

Do not write device commands into the existing dashboard-writable tables or weaken existing policies. Propose a separate, narrowly scoped control plane and review it before making database changes. Existing public memory tables must remain untouched.

## Stage 1 acceptance

- Hosting choice: GitHub Pages.
- Dashboard is cross-device browser UI; compute execution is separated into compatible device agents.
- Device capabilities and training eligibility are measured, not guessed.
- Pairing and training controls remain disabled until backend, agents, enforcement and lease checks are implemented.
- No secret values added and no training started.
