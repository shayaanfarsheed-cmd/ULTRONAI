# ULTRON — Local Training Architecture

**Status:** approved design direction. Device pairing and remote device commands are removed. No real training has started.

## Security boundary

- ULTRON will not pair remote devices, issue device credentials, maintain a device registry, or expose a dashboard-to-device command channel.
- The GitHub Pages dashboard is a monitoring and project-information surface. It cannot start, stop, pause, resume, or reconfigure a training process on another device.
- Training controls must execute on the same device/runtime that performs training. The person using that runtime selects the RAM limit and presses Start or Stop locally.
- No local control service may listen on a public interface. If a local HTTP interface is later required, bind it to loopback only, reject non-local origins, and do not expose it through a tunnel or public reverse proxy.
- No automatic training on device boot, dashboard load, browser refresh, or reconnection.
- iPad can open the dashboard and, if the selected training provider offers a notebook UI, operate that provider's own session. iPadOS browser tabs are not assumed to host a persistent Python training process.

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

Use a stub training worker and generated fixtures; do not start the real model. Test RAM cap enforcement and over-cap behavior on each supported OS, child-process containment, graceful stop, stop during batch/checkpoint, timeout escalation, duplicate starts, lease expiry, abrupt process death, corrupt checkpoint recovery, max duration, no auto-restart, and truthful status reporting. Keep actual training disabled until all required tests pass and the owner separately approves activation.

## Retired backend

The old device-control Edge Function is replaced with a fail-closed HTTP 410 response. Historical migration files and private tables are retained for auditability; they are not part of the product and must not receive browser grants or new callers. No database records or checkpoints are deleted as part of this retirement.
