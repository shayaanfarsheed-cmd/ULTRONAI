# ULTRONAI — Current implementation handoff (2026-11-18)

**Repository:** `shayaanfarsheed-cmd/ULTRONAI`  
**Main branch:** `main`  
**Latest merged work:** PR #12 — [Dashboard performance optimization](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/12), merged at `02ddff7437f6a4ac89f78c52ceb36cef6d3f944b`.  
**Current working branch:** `fix/bounded-checkpoint-streams` (follow-up hardening; PR not yet opened).

## Latest code review and follow-up

- Reviewed the merged PR #12 source, runtime helpers, checkpoint paths, behavioural tests, and handoff documentation.
- Review finding: the prior size guard checked `arrayBuffer()` only after the browser had allocated the entire response. A missing or dishonest `Content-Length` could therefore bypass the intended pre-allocation memory bound.
- Follow-up implementation: stream checkpoint response chunks and cancel immediately when the configured byte cap would be exceeded; reject unsafe non-streaming responses when no trustworthy length is available; validate declared versus actual streamed length.
- Tightened manifest step validation to require a non-negative safe integer number, rather than coercing strings.
- Added regression tests for exact-limit streams, stream cancellation, early declared-length rejection, unsafe fallback rejection, and malformed step types.
- No production Supabase changes, secrets, account provisioning, device pairing, agent installation, provider jobs, or real training.

**Validation:** follow-up code is not yet validated. Run the three required GitHub Actions workflows against the final follow-up commit before opening/merging the PR. Device compatibility testing remains outstanding.

**Next actions:** inspect the updated files and diff; run Node behavioural tests and syntax checks; run full CI; then update this handoff with the exact commit and actual results. Keep this follow-up unmerged until reviewed and validated. Do not start training.

---

# ULTRONAI — Current implementation handoff (2026-11-18)

**Repository:** `shayaanfarsheed-cmd/ULTRONAI`  
**Active branch:** `main`  
**Latest verified main commit:** `4ced9ca745aec0ab7dc736be100f5a25f7422848`  
**Merged work:** PR #10 (repository architecture/configuration baseline) and PR #11 (owner sign-in and Guest Mode dashboard foundation).  
**Latest PR:** [#11 — Build owner sign-in and Guest Mode dashboard foundation](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/11) — merged.

## Current status

- PR #11 is merged. Its squash merge commit is `4ced9ca745aec0ab7dc736be100f5a25f7422848`.
- The merged dashboard includes Guest Mode by default, owner sign-in/sign-out UI, frontend owner UUID verification, owner-only request guards, private Activity view gating, and regression tests.
- Owner sign-in remains deliberately inactive: `dashboard/config.js` contains a publishable-key placeholder and an empty `ownerUserId`.
- The frontend UUID allowlist and browser-side request guards are not backend authorization. Production RLS and trusted server-side authorization still require separate design, review, and explicit approval.
- Browser `sessionStorage` is not secure credential storage. Do not describe it as such or put privileged service-role secrets in the browser.
- Device pairing, remote device control, checkpoint operations requiring production credentials, and live training remain unavailable until their secured backend and device architecture is implemented and separately approved.
- The RAM slider is a local preference only; it does not enforce a process or operating-system memory limit.
- No owner account was created, no device was paired, no agent was installed, and no provider job or live training was started.

## Optimization work — current stage

- Starting point: merged `main` commit `4ced9ca745aec0ab7dc736be100f5a25f7422848`.
- Working branch: `optimize/dashboard-performance-security`.
- Initial read-only review identified:
  1. Possible concurrent refresh-token rotation when several requests renew an expiring session at once.
  2. Sequential checkpoint metadata/file reads that can be slow on mobile networks.
  3. Unnecessary chart redraws during full renders and window resize events.
  4. Historical README handoff statements that incorrectly described PR #11 as unmerged.
- Implemented on PR #12: single-flight refresh-token renewal; auth-generation checks against stale refreshes; checkpoint metadata concurrency capped at three; bounded metadata/file downloads (1 MiB metadata, 64 MiB per file, 256 MiB aggregate); strict manifest structure, path, SHA-256 and safe-integer validation; animation-frame fallback and defensive canvas handling.
- Added executable Node behavioural tests for bounded concurrency, valid/invalid manifests, aggregate-size rejection, and chart scheduling fallback. Python's dashboard suite now runs these tests.
- Current PR head is being validated; do not treat prior CI results as validation of these latest fixes. The README itself will trigger another validation run.
- Remaining: verify actual CI on the final README-synced commit, review any failures, and then run iPad/iPhone/Android/desktop compatibility checks. Keep PR #12 unmerged pending review and explicit user approval.
- Preserve the $0 budget, no Kaggle, no external AI APIs, no pretrained weights, and no externally generated training data.
- No production Supabase changes, secrets changes, owner provisioning, device pairing, provider jobs, or real training are authorized by this optimization task.
- Do not merge optimization work without explicit user approval.

## Validation state

- PR #11's three GitHub Actions checks passed on its validated head before merge.
- All three GitHub Actions workflows passed on implementation commit `e1729ef735157bf45dc5c514d8bddc2335235dbb`: Test Suite run `44236200315`, Training Prototype Validation run `44236200378`, and Preflight run `44236200390`.
- The subsequent README validation-sync commit `083e6d37de913efdef47d12fc9b4e12f106ceb54` was also fully validated: Test Suite run `44236363036`, Training Prototype Validation run `44236363001`, and Preflight run `44236362991` all completed successfully.
- Recheck all workflows after any further source or documentation changes; compatibility testing remains a separate phase.
- Compatibility testing across iPad/iPhone/Android/desktop remains a separate required phase after feature implementation and code repair.

---

## Work Package 1 handoff — 2026-11-18

- **PR:** [#10 — Repair repository docs and owner/guest configuration baseline](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/10)
- **Branch:** `repair/work-package-1-repository-architecture`
- **Validated PR head before this README sync:** `4b8bc0afe572e748e195d48e736eaa737b4e2f30`. All three GitHub Actions workflows passed on that exact head: Preflight `44222226674`, Training Prototype Validation `44222226690`, and Test Suite `44222226680`. This README sync creates a newer commit; recheck CI on the new exact head.
- **Base:** `main` at `397f1492c300371821b2651ddfbc7342adc9f60c`
- **PR #10 status at the validated head:** open, unmerged, and GitHub reported mergeable. All three workflows passed on the validated head listed above. Recheck mergeability and CI after this handoff-only README update.
- **Files changed:** `README.md`, `config.json`, `docs/LOCAL_AGENT_ARCHITECTURE.md`, `docs/REPOSITORY_REPAIR_AUDIT.md`, `servers.json`, `supabase/SETUP.md`, `tests/test_config.py`, `train.py`.
- **Key decisions:** one restricted owner account plus public Guest Mode; no public signup; private operations require verified owner authorization; guests are limited to public content; Kaggle disabled; resource enforcement is platform-specific and training must fail closed when not verified.
- **Not implemented:** owner login/recovery, production backend authorization, device registry/pairing, agents, and enforced resource limits.
- **Safety:** no Supabase production changes, secrets, pairing, agent installation, training, provider jobs or merges.
- **Validation:** all three workflows passed on validated head `4b8bc0afe572e748e195d48e736eaa737b4e2f30`: Preflight run `44222226674`; Training Prototype Validation run `44222226690`; Test Suite run `44222226680`. Every job step in all three runs completed successfully. GitHub reported `mergeable: true` for this head. The following README handoff update requires a fresh exact-head CI/mergeability check.

---

# ULTRONAI — Current Product Architecture and Handoff

> **Authoritative current direction (2026-11-18):** ULTRON is a browser-based, iPad-compatible mathematics training-control website. It will have one restricted owner account and a public Guest Mode. This is the target architecture, **not a claim that authentication or private controls are implemented today**.

## Current implementation truth

- Historical note: before PR #11, the dashboard had no owner sign-in UI. Current implementation (PR #11 merged) includes owner sign-in/sign-out UI and a frontend owner-session gate; production authentication remains deliberately inactive until configuration and trusted backend authorization are completed.
- Guest Mode is intended for public dashboard and public mathematics information only. It must never access private training history, checkpoints, device pairing, or remote training controls.
- The owner account is intended to be one identity across the system. Public self-registration must not create additional owner accounts. Secure owner provisioning and recovery require a separately reviewed implementation.
- Backend authorization—not hidden buttons—must protect every private operation. Owner identity must be derived from a verified server-side session. Never trust a browser-supplied owner ID.
- Device pairing, remote training controls and checkpoint operations remain locked until the owner authorization, device-control backend, agent and resource enforcement are implemented and tested.
- The dashboard RAM slider is a local preference only; it is not an operating-system memory limit.
- Device support is platform/capability based. Windows-specific assumptions must not define the whole product. iPadOS and mobile browsers are dashboard clients, not assumed training workers.
- Kaggle is excluded from the active provider plan because the user declined Kaggle. No Kaggle job or credential setup is authorized.
- Permanent constraints: $0 budget, no paid APIs/services, no pretrained weights/models, no externally generated AI training data, no exposed credentials, and no live training without separate approval.

## Current repair work

- Work Package 1 branch: `repair/work-package-1-repository-architecture`
- File-by-file audit: [docs/REPOSITORY_REPAIR_AUDIT.md](docs/REPOSITORY_REPAIR_AUDIT.md)
- Main baseline: `397f1492c300371821b2651ddfbc7342adc9f60c`
- PR #4 remains open and unmerged: [secure device-control contract](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/4).
- PR #4 current head inspected: `6fa27729b657c43719fe5955b3f1b2d609720659`; its three latest CI workflows passed (Test Suite `44218633547`, Preflight `44218633560`, Training Prototype Validation `44218633551`).
- No Supabase production changes, account creation, device pairing, agent installation, training, provider jobs or merges were performed.

**Read the repair audit before continuing.** Older operational notes below are historical and must not override this current product direction. The owner account is not yet implemented; do not follow older public self-registration instructions.

---

# ULTRON Training Control

ULTRON is an independently implemented mathematics Transformer training project. It starts from random weights, generates its own deterministic mathematics data, verifies examples independently, and does not use pretrained models, pretrained weights, AI APIs, or paid compute.

## Online website-controlled local training

The selected hosting is GitHub Pages. The intended workflow is an online dashboard on GitHub Pages, a single restricted owner identity for private control, Guest Mode for public visitors, and compatible device agents that make outbound HTTPS connections. Desktop training workers are platform-specific; iPad and mobile browsers are dashboard clients. The owner/guest authentication flow and device agents are not implemented yet.

The architecture and security contract is documented in [`docs/LOCAL_AGENT_ARCHITECTURE.md`](docs/LOCAL_AGENT_ARCHITECTURE.md). This is a design specification only: the device agents and Run/Pause/Resume/Stop integration have not yet been implemented, and training has not started.

## Local RAM budget control

The dashboard Settings page now includes a 2–10 GB RAM budget slider (0.5 GB increments), defaulting to 6 GB as a browser preference. The selected value is currently saved only in the browser where it is changed. It is a preference preview, **not an enforced process limit yet**. A compatible device agent must enforce the setting with a verified operating-system resource-control mechanism before training can start. See [the local-agent architecture](docs/LOCAL_AGENT_ARCHITECTURE.md).

## Browser dashboard

The static dashboard is in `dashboard/`. The repository root redirects to it.

## Current status — 2026-11-18 (PRs #7, #8 and #9 merged)

**This section supersedes older operational and handoff notes below wherever they conflict.**

- **Repository:** `shayaanfarsheed-cmd/ULTRONAI`
- **Latest main merge:** PR #9 squash merge `576ff758bb60391a816d1d2fb2e24d7c0fe63a81` (includes the PR #7 lease fix follow-up).
- **PR #8:** [Remove public read-only messaging and personal training history](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/8) — merged as `8e3bbfb62732de5cb47229572cac14b37cdc3d37`.
- **PR #7:** [Fail closed when training heartbeat errors approach lease expiry](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/7) — merged as `2515754cefe458937fb4bd764d7e6ad58198065c`. Reviewed the heartbeat failure path and regression tests before merging.
- **PR #7 reviewed head:** `13aec6a1d13a161793fb56ce3baee178e749c811`.
- **PR #7 CI on reviewed head:** Test Suite run `44213583636` passed; Preflight run `44213583634` passed; Training Prototype Validation run `44213583655` passed. Every listed job step completed successfully.
- **PR #9:** [Save checkpoints locally during Supabase heartbeat outages](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/9) — merged as `576ff758bb60391a816d1d2fb2e24d7c0fe63a81`.
- **PR #9 reviewed head:** `ac830806008d9d97d7b32a330e64f4aba09e3514`.
- **PR #9 CI on reviewed head:** Test Suite run `44215478054` passed; Preflight run `44215477870` passed; Training Prototype Validation run `44215477893` passed. All three workflows completed successfully.
- **PR #9 changes:** `ultron_session.py` now saves locally only on a near-expiry `SupabaseAPIError`, marks the lease lost, and stops without remote checkpoint commit or lease release. `tests/test_session.py` adds regression coverage for this exact outage path.
- **PR #4:** secure device-control contract remains open/unmerged; review separately before any merge.
- **No live training or provider jobs have been started.**

### Public dashboard requirements and current behaviour

- Guest Mode is public; the single owner account is planned but not implemented. Public self-registration must remain disabled.
- Guests must not access personal training history, checkpoints, device pairing, or remote training controls.
- Public-read-only-mode labels and the old History view have been removed.
- Checkpoint access, device pairing, automatic starts, and training controls remain unavailable/locked.
- The RAM slider is a browser-local preference only; it is not an enforced OS process limit until a secure device agent exists.

### PR #7 heartbeat and checkpoint protection

- The training loop treats unexpected heartbeat/control errors as failures and throttles retries to the configured heartbeat interval.
- Both generic heartbeat/control failures and `SupabaseAPIError` database outages now save the latest state to local storage only near lease expiry, do not attempt a remote checkpoint commit or release, mark the lease lost, and stop.
- Regression tests cover local checkpoint preservation/no remote commit on a near-expiry heartbeat failure and retry throttling.
- The PR changed `ultron_session.py`, `tests/test_session.py`, and README handoff documentation. No Supabase schema, credentials, dashboard, provider configuration, or live training jobs were changed by PR #7.

### Exact next tasks for the next chat

1. Verify `main` contains merge commit `576ff758bb60391a816d1d2fb2e24d7c0fe63a81`; PR #9's three CI workflows passed on reviewed head `ac830806008d9d97d7b32a330e64f4aba09e3514`.
2. Review PR #4's secure device-control contract separately; do not merge or deploy it without explicit user approval.
3. Resolve the owner/guest authorization design and review the device-generic agent contract before implementation. Keep outbound HTTPS polling, one-time pairing, OS secret storage, command allowlist, lease fencing, and OS-enforced RAM limits.
4. Confirm GitHub Pages deployment and manually verify the public dashboard: no login/sign-up, no personal history, and checkpoint/device/training controls remain locked.
5. Preserve the training objective: from-scratch 3–5M parameter mathematics Transformer, deterministic generated math data, independent verifier, no pretrained weights/models, no AI APIs, and no paid compute.
6. Do not start live training/provider jobs, pair devices, alter Supabase schema, or expose secrets without explicit approval.
7. Before ending any future chat/context handoff, update this README with actual main SHA, PR states, CI results, deployment state, and exact next actions.


The owner login is not implemented yet. Do not configure or expose authentication based on the historical steps below. `dashboard/config.js` currently contains a placeholder publishable key; it is public configuration, not an owner credential. Never put an `sb_secret_...` key in browser code.

To publish with GitHub Pages:

1. Open the repository **Settings → Pages**.
2. Choose **Deploy from a branch**.
3. Select branch `main` and folder `/(root)`.
4. Save and wait for the Pages deployment.
5. Open `https://shayaanfarsheed-cmd.github.io/ULTRONAI/`.

Historical setup note — do not follow this as an instruction to sign in or change production settings. Owner authentication is not implemented. Any future Supabase exposure, grants, RLS, or schema changes require a separately reviewed plan and explicit approval.

## Provider secrets

Add these values to each provider's secret manager, never to source files or notebook cells:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (current `sb_secret_...` key)
- `SUPABASE_OWNER_ID` (server-side owner UUID; not a browser credential)

The future owner dashboard may use a publishable key plus a verified owner session. The notebook and worker use backend secrets only from a trusted secret manager.

## Training entry points

- `train.ipynb`: browser notebook launcher for supported notebook platforms; Kaggle is excluded from the active provider plan.
- `train.py`: shared training entry point.
- `ultron_model.py`: model architecture.
- `ultron_data.py` and `ultron_verify.py`: deterministic mathematics generation and independent verification.
- `ultron_checkpoint.py`: local atomic checkpoint creation and verification.
- `ultron_storage.py`: private Supabase checkpoint upload and recovery.
- `ultron_supabase.py`: status, lease, heartbeat and checkpoint database client.
- `ultron_session.py`: training session orchestration.
- `ultron_switcher.py`: guided and allowlisted automatic server selection.

## Current operational limits

- The database-side lease functions and private bucket are installed in Supabase.
- The dashboard source is committed, but GitHub Pages still needs to be enabled and the publishable key added to `dashboard/config.js`.
- The training worker currently expects a server-side owner UUID and backend secret from its secret manager. This is separate from the future browser owner session; do not create public self-registration or put backend credentials in the website.
- The notebook has not yet been run on any live provider account.
- Secondary Hugging Face checkpoint backup and ONNX release are not yet complete.
- Provider account quota and GPU availability must be checked in each provider account.

## Automated tests

The repository test workflow runs on pushes and pull requests. It checks the Python modules, deterministic data generator, model, checkpoint recovery, Supabase lease client, dashboard JavaScript, JSON configuration and notebook structure.

For a browser-free local validation environment with Python 3.11 and CPU PyTorch installed:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python train.py --preflight --model-summary --data-smoke-test --checkpoint-smoke-test --training-smoke-test
node --check dashboard/app.js
node --check dashboard/config.js
```

## Mandatory next-chat handoff rule (current)

**This section supersedes the older handoff notes further below.** At the end of every ChatGPT work session, before the conversation context is closed or handed to a new chat, update this README with a concise, factual handoff. Do not assume the next chat can see the previous conversation.

Every handoff must record:
- Date/time (UTC), repository, active branch, latest commit SHA, and open PR number/link.
- What changed in this session and the exact files touched.
- Tests and CI runs with their actual results; clearly label anything still running, failed, or not yet verified.
- Current deployment/runtime state and known limitations.
- The next tasks in priority order, including the exact first file or test to inspect.
- Outstanding user decisions/approvals. Never imply approval to merge or start training.
- Secret names and where they belong (provider secret manager only), never secret values.

Before finishing a chat, verify the current GitHub branch/commit/PR and CI state, then update this section. In the next chat, read this section first, inspect the referenced commit and files, and continue from that state. Do not repeat completed work or overwrite newer changes. If no code changed, still update the handoff date and next action when the project state or test status changed.

### Latest handoff — 2026-11-18

- **Handoff timestamp:** 2026-11-18 01:25 UTC
- **Repository:** `shayaanfarsheed-cmd/ULTRONAI`
- **Main merge commit:** `576ff758bb60391a816d1d2fb2e24d7c0fe63a81` (PR #9).
- **PR #9:** merged after code review and all three CI workflows passed on exact head `ac830806008d9d97d7b32a330e64f4aba09e3514`.
- **PR #9 CI:** Test Suite `44215478054` success; Preflight `44215477870` success; Training Prototype Validation `44215477893` success.
- **Fix:** Supabase database heartbeat failures now persist locally only near lease expiry, set `lease_lost`, and stop without remote checkpoint commit or lease release. Regression test `test_database_heartbeat_error_saves_locally_without_remote_commit` added.
- **PR #7 and PR #8:** remain merged. **PR #4:** remains open/unmerged and requires separate security review.
- **Training status:** no live training/provider job started; no Supabase schema or secret changes.
- **PR #8:** merged; public dashboard history/login cleanup.
- **PR #4:** remains open/unmerged and needs a separate security review.
- **Latest validated PR #7 head:** `13aec6a1d13a161793fb56ce3baee178e749c811`.
- **CI:** all three PR #7 workflows passed on that exact head: runs `44213583636`, `44213583634`, and `44213583655`. All job steps succeeded.
- **Files changed by PR #7:** `ultron_session.py` and `tests/test_session.py`; README was also updated for the handoff.
- **Training status:** no live training/provider job started; no Supabase schema or secret changes made.

#### Next actions

1. Verify the latest `main` SHA and post-merge CI runs after PR #7.
2. Review PR #4 separately; do not merge or deploy it without explicit approval.
3. Continue the device-generic agent architecture and platform-specific enforcement review only after the device-control contract review.
4. Confirm GitHub Pages deployment and public-dashboard locked-control behaviour.
5. Keep secrets in provider secret managers only. Never request or record secret values.
6. Update this README again before any future chat handoff.

## Current development status and next-chat handoff

**Latest handoff:** 2026-11-18 05:15 UTC  
**Repository:** `shayaanfarsheed-cmd/ULTRONAI`  
**Active branch:** `optimize/dashboard-performance-security`  
**PR #12:** open, draft, unmerged — [Dashboard performance optimization](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/12).

Latest repair files: `dashboard/runtime.js`, `dashboard/app.js`, `dashboard/index.html`, `tests/dashboard_runtime.test.js`, and `tests/test_dashboard.py`. Checkpoint metadata is capped at 1 MiB, individual checkpoint objects at 64 MiB, and total checkpoint data at 256 MiB; manifest file names, sizes, hashes, step values, and required state file are validated before use. Chart drawing now has a safe fallback when animation-frame or canvas support is unavailable. Behavioural tests exercise concurrency, malformed metadata, size limits, and chart scheduling.

**Validation:** the new code has not yet been validated by GitHub Actions on its final commit. Previous PR #12 workflow successes apply only to the earlier head and must not be carried forward as evidence for these fixes. Compatibility testing is not yet complete.

**Next action:** inspect the latest PR head and run all three required GitHub Actions workflows; fix failures, update this handoff, and revalidate the README-synced final commit. Keep PR #12 unmerged until review is complete and the user explicitly approves. Do not start training or change production Supabase settings.



**Last updated:** 2026-11-17 13:35 UTC  
**Repository:** `shayaanfarsheed-cmd/ULTRONAI`  
**Working branch:** `main`  
**Latest commit at handoff:** `7950a9b2eab54fe3584dd8c2a3823011d232b357` — "Add verified secondary backup fallback and retry pending primary commits"

This section is the source of truth for continuing work in a new ChatGPT conversation. Read it before editing files. Continue from the existing code; do not rebuild the project or repeat completed work.

### Overall objective and non-negotiable rules

Build ULTRON as a 3–5 million parameter mathematics Transformer trained from random initialization, using only its own deterministic math-data generator and independent verifier. No pretrained models, pretrained weights, AI APIs, paid compute, or user's laptop. The user works from an iPad/browser. Keep the training workflow resumable across free cloud providers, with a browser dashboard and Supabase coordination.

Work in small stages. Inspect files before editing. After every change, run the relevant tests and then the full suite. Never say a test passed unless its result was actually observed. Do not start live model training or ask the user to paste secrets into chat.

### What already exists

- `servers.json`: editable provider order, links, hardware and provider-limit metadata.
- `config.json`: editable training, model, checkpoint, heartbeat, quota, coordination and dashboard settings.
- `train.py` and `train.ipynb`: common training entry points.
- `ultron_model.py`: from-scratch Transformer; configured and measured at 4,038,478 parameters.
- `ultron_data.py` and `ultron_verify.py`: deterministic math generation and separate verification.
- `ultron_checkpoint.py`: local checkpoint creation, checksums and recovery.
- `ultron_storage.py`: Supabase checkpoint storage plus the newly added private Hugging Face backup store.
- `ultron_supabase.py`: Supabase status, heartbeat, lease/fencing and checkpoint coordination.
- `ultron_session.py`: training loop and session orchestration.
- `ultron_switcher.py`: server selection and switching logic.
- `dashboard/`: static browser dashboard.
- `supabase/`: SQL/setup material and backend configuration.
- `tests/`: automated tests.
- GitHub Actions workflow: runs repository checks on supported pushes and pull requests.

The Supabase database-side lease functions and private checkpoint bucket were previously installed. Confirm live schema, policies and bucket settings before changing them.

### Work completed immediately before this handoff

The earlier task was **secondary checkpoint backup and recovery**; current priority is finishing the website and owner/guest architecture before training. The following changes have been committed to `main`:

1. Added `huggingface_hub` to `requirements.txt`.
2. Added `HuggingFaceCheckpointStore` to `ultron_storage.py`. It requires an existing private Hugging Face model repository, uploads immutable checkpoint folders, stores a manifest receipt, and verifies component sizes and SHA-256 hashes.
3. Added fake-provider tests for private Hugging Face upload/download round-trip and rejection of a public repository in `tests/test_storage.py`.
4. Added optional `HF_TOKEN` and `HF_REPO_ID` loading to the training setup. These must come from each platform's secret manager; never hard-code or print them.
5. Added settings for secondary backup cadence, backup-on-primary-failure, backup-on-handoff, and retention in `config.json`.
6. Integrated secondary backup candidate discovery and restore into `ultron_session.py`. If a secondary candidate is corrupt, startup should fall back to verified Supabase candidates.
7. Added retry handling for a checkpoint that has a verified secondary copy but whose Supabase commit failed.

Important commit sequence:
- `7bef22d95ae873f9e9b8305e90d8e0961a3bfc71` — add Hugging Face Hub dependency.
- `1675d07ba6b0556c96b70b9ba8708ac90f85a6ee` — add secondary-backup unit tests.
- `9b2a76c032ea3431c43e33798787c773c69bf425` — integrate backup restore into training startup.
- `8b141fd03f05f52997cbdf77a7ed4ac34480b9de` — fall back to Supabase if a secondary backup is corrupt.
- `7950a9b2eab54fe3584dd8c2a3823011d232b357` — retry pending primary commits and back up on primary failure.

### Test status — do not overstate

A previous GitHub Actions run, **before the latest Hugging Face integration**, reported 87/87 unit tests passing, plus Python compilation, dashboard JavaScript checks, JSON/notebook validation, model parameter-count checks, 100/100 generated math examples verified, checkpoint save/restore and CPU smoke tests.

The Hugging Face integration commits above were made after that run. A lookup for workflow runs on the latest commit returned no runs. Therefore:

- The previous 87-test result is historical and does **not** validate the latest changes.
- The two new Hugging Face tests have been added but are **not yet confirmed passing**.
- End-to-end training recovery from Hugging Face has **not yet been tested**.
- No real Hugging Face repository has been created or connected.
- No live provider training session has been run.
- Do not claim the system is production-ready.

### Exact next tasks — do these in order

1. **Review the new backup integration carefully.** Re-read the latest versions of `ultron_storage.py`, `ultron_session.py`, `tests/test_storage.py`, `train.py`, `train.ipynb`, `requirements.txt` and `config.json`. Check for import errors, incorrect API arguments, path handling, receipt/manifest mismatches, partial uploads and exception handling.
2. **Protect the one-writer lease.** A secondary backup is not permission to keep training after the Supabase lease/heartbeat has expired. If Supabase is unreachable, stop before the locally known lease deadline, do not let another worker overlap, and make the offline-recovery behaviour explicit and tested. Never extend a lease only in local memory. Verify fencing tokens before every primary checkpoint commit.
3. **Run the full CI test suite on the current `main` commit.** Run Python compilation, `python -m unittest discover -s tests -v`, the `train.py` preflight/model/data/checkpoint/training smoke tests, `node --check dashboard/app.js`, `node --check dashboard/config.js`, JSON parsing and notebook structure checks. Capture the actual result and fix failures before continuing.
4. **Add integration tests** for: restore from a newer verified Hugging Face checkpoint when Supabase's committed pointer is older; fallback to Supabase when the newest Hugging Face checkpoint is corrupt; retry a pending Supabase commit after a temporary outage; stop safely when the lease cannot be renewed; and refuse a stale fencing token.
5. **Review checkpoint retention and backup policy.** Supabase keeps the configured last three verified checkpoints. The Hugging Face backup currently uses `keep_all`; decide whether this is acceptable for free storage or implement safe retention only after a newer backup has been downloaded and verified. Never delete the only good copy.
6. **Re-run all tests after every fix**, then inspect the final GitHub Actions result. Update this README with the real test count, commit SHA and remaining limitations.
7. Only after the backup/recovery tests pass, continue the remaining dashboard deployment, provider setup and iPad handover work. Do not start training automatically.

### Secret setup for the optional secondary backup

The user must create a **private** Hugging Face model repository and add these two secrets in each provider's secret manager:

- `HF_TOKEN`: a Hugging Face token with write access to that private repository.
- `HF_REPO_ID`: repository identifier in `owner/repository` form.

These are optional until the private repository is configured. The Supabase backend secret remains in provider secret managers only. The website must never receive either secret. Do not request secret values in chat, commit them, print them, or include them in notebook outputs.

### Current operational state

- Dashboard source is committed; GitHub Pages still needs to be enabled and `dashboard/config.js` needs the Supabase publishable/anon key.
- Owner authentication and trusted backend authorization are not implemented yet; do not create accounts or start a live training run as part of this work package.
- The user primarily works from an iPad; all website setup instructions must work in a browser and must not assume a Windows device.
- Live provider accounts, actual quotas, GPU availability, Hugging Face private storage, browser sign-in and cross-provider recovery still need user-side setup or live verification.
- Keep automatic starts disabled until platform policy, secrets and safety limits are verified. Guided switching must remain available.


## PR #4 security review and repair plan — 2026-11-18

**PR:** [#4 — Define secure ULTRON device control contract](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/4)  
**Reviewed head:** `1bac6ba86b60576f19cc70ffd1504c049f2ef1d4`  
**Status:** Open, not merged. Contract/schema/tests only; no device-control backend or agent is deployed.

### Review conclusion

The proposal has good foundational boundaries: no arbitrary shell/script commands, owner-bound authorization, one-time pairing, outbound-only agent polling, per-device credentials, lease fencing, and explicit OS memory-enforcement requirements. It is not implementation-ready yet. The existing six tests mostly inspect schema structure and do not execute the JSON Schema against valid and adversarial command instances.

Key gaps to resolve before implementation:
1. Define the complete database security model: exact table columns/constraints/indexes, non-exposed schema grants, service-role-only writes, Edge Function JWT verification, and negative cross-owner tests. The current proposal says "private schema" but does not spell out the actual grants/RLS model.
2. Define atomic command claiming and idempotency: transaction/locking semantics, claim lease/timeout, retry behaviour, duplicate acknowledgement, ordering, and what happens when an agent crashes after claiming but before execution/acknowledgement.
3. Define command time semantics: server-authoritative expiry, maximum command lifetime, issued/expiry relationship, clock-skew tolerance, stale/replayed command rejection, and bounded result payloads.
4. Define credential lifecycle: token entropy/encoding, cryptographic hash choice for high-entropy secrets, one-time display, rotation, overlap/revocation behaviour, recovery after OS key-store loss, and redaction from all logs.
5. Tighten lease fencing: authoritative lease validation and token comparison immediately before process launch and before every checkpoint/side effect; local agent must stop on lease uncertainty, revocation, stale token, or heartbeat timeout. Specify the stop deadline and crash recovery.
6. Make resource enforcement testable: Windows Job Object assignment and Linux cgroup v2 delegation/limits, explicit rejection when unavailable, measured memory headroom, and platform-specific integration tests. macOS stays ineligible until an enforceable cap is proven.
7. Specify the local agent trust boundary: signed/reproducible releases, update verification/rollback, installation-directory permissions, process ownership, safe termination, secure local IPC, and protection against another local user altering the executable/config.
8. Add actual JSON Schema validator tests for each action and invalid cases. Validate UUID/date-time formats, action-specific parameter combinations, unknown fields, boundary values, and expiry policy. The schema alone cannot enforce dynamic facts such as expiry relative to server time or current fencing token.

### Ordered repair plan

1. **Contract hardening (docs/schema/tests only):** write explicit database grants/RLS and Edge Function auth requirements; define atomic state transitions for pairing and command claim/ack; define token lifecycle, time bounds, lease-loss behaviour, and platform eligibility. Replace structural-only tests with validator-driven positive and negative fixtures.
2. **Threat model and state-machine review:** document attacker capabilities (malicious browser, stolen pairing code, stolen device credential, compromised local user, replayed network request, stale worker); draw pairing, command, revocation, lease and shutdown state transitions. Add failure-injection tests.
3. **Backend design review (no deployment yet):** produce migration SQL and Edge Function contracts separately, including least-privilege grants, owner scoping, rate limits, audit events, atomic SQL/RPC operations, and secret redaction. Review all SQL and function code before requesting approval.
4. **Approval gate:** request explicit approval before any Supabase migration, Edge Function deployment, RLS/grant change, or secret configuration. Keep the public dashboard controls disabled until end-to-end security tests pass.
5. **Agent prototype:** begin with status-only polling and a fake command server. Add platform-specific agents only after their OS credential storage, signed update verification, fixed training entry point, enforceable memory cap, and lease-loss fail-stop behaviour are proven. Do not enable start until tests prove enforcement.
6. **Platform expansion:** add Linux only after cgroup v2 enforcement tests; keep macOS and mobile browsers as monitoring/control clients until their enforcement and runtime constraints are independently proven.
7. **End-to-end validation:** test cross-user isolation, concurrent pairing redemption, credential theft/revocation, command replay/expiry, claim crashes, stale fencing tokens, duplicate delivery, process-tree termination, memory-limit refusal, and recovery after agent restart. Run all repository CI on the refreshed PR head.
8. **Merge decision:** update PR #4 against current `main`, incorporate contract/test fixes, run CI, review the final diff, then merge only after all checks pass and explicit approval.

**Do not do yet:** no Supabase schema changes, Edge Functions, device pairing, agent installation, live training, or unlocking dashboard controls. PR #4 should remain unmerged until the contract and executable tests are hardened.