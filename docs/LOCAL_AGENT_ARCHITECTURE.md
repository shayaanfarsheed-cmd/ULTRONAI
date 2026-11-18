# ULTRON — Local Training Architecture

**Status:** local-only dummy-worker lifecycle prototype added on branch `runtime/local-dummy-worker`. Device pairing and remote device commands are removed. No real training has started.

## Security boundary

- ULTRON will not pair remote devices, issue device credentials, maintain a device registry, or expose a dashboard-to-device command channel.
- The GitHub Pages dashboard is a monitoring and project-information surface. It cannot start, stop, pause, resume, or reconfigure a training process on another device.
- Training controls must execute on the same device/runtime that performs training. The person using that runtime selects the RAM limit and presses Start or Stop locally.
- No local control service may listen on a public interface. If a local HTTP interface is later required, bind it to loopback only, reject non-local origins, and do not expose it through a tunnel or public reverse proxy.
- No automatic training on device boot, dashboard load, browser refresh, or reconnection.
- iPad can open the dashboard and, if the selected training provider offers a notebook UI, operate that provider's own session. iPadOS browser tabs are not assumed to host a persistent Python training process.

## Implemented prototype boundary (2026-11-18)

- `ultron_local_runtime.py` is a local command-line lifecycle harness that launches only a dummy subprocess. It has no HTTP listener, network client, Supabase integration, provider automation, model import, or training entry point.
- Commands are explicit on the same device: `python ultron_local_runtime.py start`, `stop`, `status`, and `verify`. The default state directory is `.ultron-local`.
- Stop is represented by a local stop-request file and observed by the dummy worker at a batch boundary. Checkpoints are written to a temporary file, flushed, atomically replaced, and SHA-256 verified.
- A lock rejects duplicate starts and fails closed on stale/corrupt lock state; there is no automatic recovery or restart. On Linux, process-exit detection treats `/proc` states Z (zombie) and X (dead) as no longer executing and compares `/proc` start-time ticks to avoid confusing a reused PID with the original worker. Status also fails closed when the process record is missing or belongs to a different run. Non-procfs platforms still use a conservative signal-zero check and do not yet have equivalent PID-reuse identity verification.
- **RAM enforcement is not implemented.** A request for a hard RAM cap is refused before process start. The prototype must not be connected to the model or presented as a usable training runtime.
- The dummy-worker tests are lifecycle tests only; they do not prove OS-level RAM enforcement, process-tree containment, cross-platform behavior, or model checkpoint compatibility.

## Local control design

1. The person at the training runtime chooses a RAM ceiling before starting.
2. Preflight detects platform support and verifies the selected limit can be enforced for the full training process and its child processes.
3. Start requires an explicit local action. A second process or duplicate click cannot start a second trainer; a single-writer lease protects checkpoints.
4. The training loop checks a local stop signal at safe batch boundaries, stops accepting new work, writes an atomic checkpoint, validates it, and exits.
5. Stop is idempotent. UI states distinguish stop requested, checkpointing, stopped, and failed; never report stopped until the process has exited.
6. If graceful stop times out, preserve the last verified checkpoint and terminate the worker. Force termination may lose the current uncheckpointed batch and must be reported honestly.
7. A locally configured maximum duration may stop training automatically; it is optional and enforced by the training process itself, including while offline.

## RAM enforcement

The browser slider is only a preference until the local runtime confirms enforcement. Display three separate values: requested RAM, enforced cap/mode, and measured current/peak usage.

- Linux: use cgroups v2 or a verified systemd scope; confirm the effective memory.max before training.
- Windows: use a Job Object with a job-wide memory limit where supported; do not confuse a per-process limit with a process-tree cap.
- macOS: do not claim a hard cap until an enforceable mechanism is independently verified. If unavailable, refuse a hard-cap start rather than silently downgrade.
- Browser-only/iPadOS: cannot impose an OS-level cap on an external Python process. Do not represent the dashboard RAM preference as enforcement.

If the platform cannot enforce the selected cap, Start remains disabled and the UI explains why.

## Stop and checkpoint failure handling

- Stop request during a batch: finish only the current safe unit, then checkpoint and exit.
- Stop request during checkpoint: serialize the request; never interrupt the atomic replace step.
- Corrupt checkpoint: keep the previous valid checkpoint and mark the run failed; never overwrite the only good copy.
- Process crash or power loss: recover only from a validated checkpoint and require a new local Start action.
- Memory pressure/OOM: record the failure, retain the last valid checkpoint, and do not auto-restart.
- Duplicate start: reject it while an active process or unexpired lease exists.
- Stale stop or stale session: scope the local stop signal to a run ID and generation so it cannot affect a later run.
- Dashboard closed or network lost: local training continues only according to the local runtime's policy; the website does not own the process lifecycle.

## Tests required before activation

Use a stub training worker and generated fixtures; do not start the real model. The current dummy prototype covers explicit start, duplicate-start rejection, local stop at a batch boundary, atomic checkpoint verification, corrupt checkpoint rejection, stale-lock fail-closed behavior, and refusal of unsupported hard-RAM-cap requests. Still required before any real runtime: verified RAM cap enforcement and over-cap behavior on each supported OS, child-process containment, stop during checkpoint, timeout escalation, abrupt process death, previous-valid-checkpoint preservation, maximum duration, and truthful process-exit reporting. Keep actual training disabled until all required tests pass and the owner separately approves activation.

## Retired backend

The old device-control Edge Function is replaced with a fail-closed HTTP 410 response. Historical migration files and private tables are retained for auditability; they are not part of the product and must not receive browser grants or new callers. No database records or checkpoints are deleted as part of this retirement.
