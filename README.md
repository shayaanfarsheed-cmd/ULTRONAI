# ULTRON Training Control

ULTRON is an independently implemented mathematics Transformer training project. It starts from random weights, generates its own deterministic mathematics data, verifies examples independently, and does not use pretrained models, pretrained weights, AI APIs, or paid compute.

## Online website-controlled local training

The selected hosting is GitHub Pages. The intended workflow is an online dashboard on GitHub Pages, Supabase for authenticated control and coordination, and a Windows local agent that makes outbound HTTPS connections and starts the fixed ULTRON training entry point only after local preflight and lease checks. This allows an iPad browser to control a paired Windows computer without exposing an inbound port.

The architecture and security contract is documented in [`docs/LOCAL_AGENT_ARCHITECTURE.md`](docs/LOCAL_AGENT_ARCHITECTURE.md). This is a design specification only: the Windows agent and Run/Pause/Resume/Stop integration have not yet been implemented, and training has not started.

## Local RAM budget control

The dashboard Settings page now includes a 2–10 GB RAM budget slider (0.5 GB increments), defaulting to 6 GB for the 16 GB Windows laptop. The selected value is currently saved only in the browser where it is changed. It is a preference preview, **not an enforced process limit yet**. The Windows agent must be implemented to receive the setting and enforce it with a Windows Job Object before training can start. See [the local-agent architecture](docs/LOCAL_AGENT_ARCHITECTURE.md).

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

- The dashboard is public; no login or sign-up is required.
- Personal/account-specific training history is not displayed or fetched in public mode.
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
3. Inspect and implement the secure Windows local agent only after reviewing PR #4's contract. Keep outbound HTTPS polling, one-time pairing, OS secret storage, command allowlist, lease fencing, and OS-enforced RAM limits.
4. Confirm GitHub Pages deployment and manually verify the public dashboard: no login/sign-up, no personal history, and checkpoint/device/training controls remain locked.
5. Preserve the training objective: from-scratch 3–5M parameter mathematics Transformer, deterministic generated math data, independent verifier, no pretrained weights/models, no AI APIs, and no paid compute.
6. Do not start live training/provider jobs, pair devices, alter Supabase schema, or expose secrets without explicit approval.
7. Before ending any future chat/context handoff, update this README with actual main SHA, PR states, CI results, deployment state, and exact next actions.


Before the dashboard can sign in, edit `dashboard/config.js` and replace `sb_publishable_REPLACE_WITH_YOUR_KEY` with the Supabase publishable/anon key for the `ultron-memory` project. This key is public by design. Never put an `sb_secret_...` key in this file.

To publish with GitHub Pages:

1. Open the repository **Settings → Pages**.
2. Choose **Deploy from a branch**.
3. Select branch `main` and folder `/(root)`.
4. Save and wait for the Pages deployment.
5. Open `https://shayaanfarsheed-cmd.github.io/ULTRONAI/`.

The dashboard requires `training_api` to be the only exposed Data API schema. Follow `supabase/SETUP.md` before signing in.

## Provider secrets

Add these values to each provider's secret manager, never to source files or notebook cells:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (current `sb_secret_...` key)
- `SUPABASE_OWNER_ID` (your Supabase Auth user UUID)

The dashboard uses only the publishable/anon key and the signed-in user's JWT. The notebook and switcher use the backend secret.

## Training entry points

- `train.ipynb`: browser notebook launcher for Kaggle, Colab and other notebook platforms.
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
- A Supabase Auth user must be created before the notebook can create a run.
- The notebook has not yet been run on the user's live Kaggle, Colab or Lightning accounts.
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
3. Continue secure Windows agent implementation only after the device-control contract review.
4. Confirm GitHub Pages deployment and public-dashboard locked-control behaviour.
5. Keep secrets in provider secret managers only. Never request or record secret values.
6. Update this README again before any future chat handoff.

## Current development status and next-chat handoff

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

The current task is **secondary checkpoint backup and recovery**. The following changes have been committed to `main`:

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
- No live Kaggle, Colab or Lightning training session has been run.
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
- A Supabase Auth user must exist before a live training run can be created.
- The user has an iPad and no laptop; all setup instructions must use browser interfaces.
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
6. Make resource enforcement testable: Windows Job Object assignment before child execution (including descendants), Linux cgroup v2 delegation/limits, explicit rejection when unavailable, measured memory headroom, and platform-specific integration tests. macOS stays ineligible until an enforceable cap is proven.
7. Specify the local agent trust boundary: signed/reproducible releases, update verification/rollback, installation-directory permissions, process ownership, safe termination, secure local IPC, and protection against another local user altering the executable/config.
8. Add actual JSON Schema validator tests for each action and invalid cases. Validate UUID/date-time formats, action-specific parameter combinations, unknown fields, boundary values, and expiry policy. The schema alone cannot enforce dynamic facts such as expiry relative to server time or current fencing token.

### Ordered repair plan

1. **Contract hardening (docs/schema/tests only):** write explicit database grants/RLS and Edge Function auth requirements; define atomic state transitions for pairing and command claim/ack; define token lifecycle, time bounds, lease-loss behaviour, and platform eligibility. Replace structural-only tests with validator-driven positive and negative fixtures.
2. **Threat model and state-machine review:** document attacker capabilities (malicious browser, stolen pairing code, stolen device credential, compromised local user, replayed network request, stale worker); draw pairing, command, revocation, lease and shutdown state transitions. Add failure-injection tests.
3. **Backend design review (no deployment yet):** produce migration SQL and Edge Function contracts separately, including least-privilege grants, owner scoping, rate limits, audit events, atomic SQL/RPC operations, and secret redaction. Review all SQL and function code before requesting approval.
4. **Approval gate:** request explicit approval before any Supabase migration, Edge Function deployment, RLS/grant change, or secret configuration. Keep the public dashboard controls disabled until end-to-end security tests pass.
5. **Agent prototype:** begin with status-only polling and a fake command server. Add Windows first with OS secret storage, signed package/update verification, fixed training entry point, Job Object memory cap, and lease-loss fail-stop behaviour. Do not enable start until tests prove enforcement.
6. **Platform expansion:** add Linux only after cgroup v2 enforcement tests; keep macOS and mobile browsers as monitoring/control clients until their enforcement and runtime constraints are independently proven.
7. **End-to-end validation:** test cross-user isolation, concurrent pairing redemption, credential theft/revocation, command replay/expiry, claim crashes, stale fencing tokens, duplicate delivery, process-tree termination, memory-limit refusal, and recovery after agent restart. Run all repository CI on the refreshed PR head.
8. **Merge decision:** update PR #4 against current `main`, incorporate contract/test fixes, run CI, review the final diff, then merge only after all checks pass and explicit approval.

**Do not do yet:** no Supabase schema changes, Edge Functions, device pairing, agent installation, live training, or unlocking dashboard controls. PR #4 should remain unmerged until the contract and executable tests are hardened.

## Latest authoritative handoff — 2026-11-18 (Stage 1 in progress)

**This section supersedes older README statements wherever they conflict.**

### Permanent project requirements
- Total project budget: **$0**. Use only genuinely free tiers and open-source software. No paid subscriptions, paid compute, paid APIs, billing activation, or expiring free trials. Verify provider limits before relying on them.
- Public GitHub Pages dashboard remains no-login/no-sign-up. Do not add authentication UI without explicit approval. Because an anonymous public browser cannot establish an owner identity, device pairing and privileged controls remain disabled until a separately approved secure owner-authorization design exists.
- No live training, provider jobs, device pairing, Supabase schema/RLS/grant changes, Edge Function deployment, production secret changes, or PR merge without the relevant explicit approval.
- No pretrained models/weights or AI APIs. The mathematics model is trained from random initialization.

### Verified repository state
- Repository: `shayaanfarsheed-cmd/ULTRONAI`
- Main at start of this work: `397f1492c300371821b2651ddfbc7342adc9f60c`
- PR #4: https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/4
- PR #4 was open and unmerged; its original head was `1bac6ba86b60576f19cc70ffd1504c049f2ef1d4`.
- PR #4's original base was old (`f18b2f2732d37b7907632f796a493ff374c66305`); current main had advanced to `397f1492c300371821b2651ddfbc7342adc9f60c`.
- Original PR #4 CI runs: Test Suite `44108898704` and preflight `44108898794` succeeded on the old head. These results do not validate the new Stage 1 changes.

### Stage 1 changes pushed to PR #4 branch
A merge commit brought current main into the PR branch while preserving the PR history:
- Stage 1 initial merge commit: `afd90911299f3684f97d74ff4aa2d3bf18eb6c64`
- Latest validated code/test commit (before this README-only handoff update): `468de41ff72f13c74e08fbb194119327ef59a834`
- Commit message: Harden device command contract and add executable validation
- Updated `docs/DEVICE_CONTROL_CONTRACT.md`: precise data constraints/indexes, non-exposed schema grants/RLS requirements, no-login authorization boundary, pairing and credential lifecycle, atomic claim/ack state machine, 120-second command TTL, 30-second clock-skew tolerance, replay protection, fencing, 10-second stop target, Windows/Linux memory enforcement, local-agent trust boundary, and explicit deployment approval gate.
- Updated `schemas/device-command.schema.json`: strict Draft 2020-12 command schema.
- Added `ultron_device_contract.py`: pure schema/time/fencing/replay-policy validation; it does not authenticate devices or replace authoritative server checks.
- Replaced structural-only tests in `tests/test_device_contract.py` with validator-driven valid/adversarial fixtures and runtime policy tests.
- Added `jsonschema[format]>=4.20,<5` to `requirements.txt` so UUID and RFC 3339 date-time formats are checked.
- Updated `.github/workflows/preflight-tests.yml` to install the schema-validation dependency.

### Validation status
- The original PR #4 Test Suite and preflight jobs passed, but they ran before the new Stage 1 changes.
- Fresh CI on validated code/test commit `468de41ff72f13c74e08fbb194119327ef59a834` passed all three workflows: Test Suite `44217450668`, preflight `44217450769`, and Training Prototype Validation `44217450665`.
- Preflight and Training Prototype Validation unit-test steps both completed successfully; the Test Suite also completed compilation, dashboard checks, configuration validation, unit tests, and model/data/checkpoint/training smoke tests successfully.
- A supplemental isolated local fixture ran all 24 device-contract tests successfully. A direct repository clone was unavailable in the execution environment, so GitHub Actions is the authoritative repository validation.
- Check that all workflows triggered by the updated PR head pass, including Test Suite, preflight, and Training Prototype Validation if applicable.

### Next actions (in order)
1. Verify PR #4 targets current main and inspect the latest head created by this README-only handoff update.
2. Inspect the complete updated diff, especially validator edge cases, action-specific parameter restrictions, and documentation consistency.
3. Verify CI on the latest README-only head; source/test code was last validated on `468de41ff72f13c74e08fbb194119327ef59a834`.
4. Check whether the schema validator's date-time/UUID format checks behave as expected under the pinned Python 3.11 workflow.
5. Ensure no public login/sign-up UI or privileged dashboard controls were introduced.
6. Keep PR #4 open and unmerged until explicit approval.
7. Do not deploy Supabase changes, pair devices, install agents, start live training, or enable dashboard controls.
8. Update this handoff with actual fresh CI run IDs/results before ending the next work session.

## Stage 2 — Threat model and state-machine review (2026-11-18)

- Added `docs/DEVICE_CONTROL_THREAT_MODEL.md` on PR #4 branch.
- Covers assets, actors, trust assumptions, 18 threat scenarios, pairing/device/command/credential/lease/process-shutdown state machines, 20 failure-injection cases, residual risks, and approval gates.
- Reaffirms the public dashboard remains no-login/no-sign-up. Device pairing and privileged controls remain disabled until a separately approved owner-authorization design exists.
- This is documentation only. No Supabase schema/RLS/grants, Edge Functions, production secrets, device pairing, agent deployment, live training, paid services, or billing were changed or started.
- Next: review the threat model against the command contract, then design Stage 3 backend contracts and SQL for review only. Do not deploy or alter Supabase without explicit approval.
- Keep PR #4 open and unmerged until explicit approval.

### Stage 2 validation
- Threat-model documentation commit: `e90a0079539d7f3632375974998f3ccbc9171235`.
- Stage 2 README handoff/code head: `2d529f2f8ea019ec5c019b553313dcb401f6e670`.
- All three workflows passed on that exact Stage 2 head: Test Suite `44217854553`, preflight `44217854500`, and Training Prototype Validation `44217854478`.
- Test Suite compilation, dashboard checks, configuration validation, unit tests, and model/data/checkpoint/training smoke tests succeeded. Preflight and Training Prototype Validation also completed successfully.
- No Supabase, production, pairing, agent, live-training, paid-service, or billing operations were performed.

## Stage 3 — Backend architecture review (2026-11-18)

- Added `docs/BACKEND_ARCHITECTURE_REVIEW.md` on the PR #4 branch.
- Reviewed the current `training_api` schema, lease/checkpoint RPCs, private checkpoint bucket policies, Python client/tests, setup guide, and local-agent architecture.
- Recommendation: keep the device-control plane in a separate non-public schema; do not add device commands to the existing training tables or create a second training lease. Use a minimal trusted Edge Function boundary, server-derived owner identity, atomic per-device command claims, durable replay protection, idempotent acknowledgement, and the existing training lease/fencing checks.
- Identified a blocking documentation/product contradiction: the public dashboard requirement is no-login/no-sign-up, while `supabase/SETUP.md` and `docs/LOCAL_AGENT_ARCHITECTURE.md` still describe Supabase Auth sign-in/account creation. Anonymous public users cannot securely authorize owner-specific device control. Interim decision: keep pairing, owner-specific device operations, and privileged controls disabled until an owner-authorization model is explicitly chosen and approved.
- This is a design review only. No Supabase project was connected or modified; no migration, RLS/grant change, Edge Function, production secret, pairing, agent, live training, paid service, billing, or PR merge was performed.
- Exact next task: resolve the no-login versus owner-authorization product decision, then prepare migration-by-migration SQL/RPC/Edge Function implementation proposals and executable authorization/concurrency tests for review. Obtain explicit approval before any Supabase change.

### Stage 3 repository and CI handoff

- Review document commit: `c7ae36f1f10c2587d0810524aad02de059c48ba3`.
- Verified review document blob: `0456c80b7a94fbbbbcd9437dcf6fdf15effded2b`.
- PR #4 remains open and unmerged; its base is main `397f1492c300371821b2651ddfbc7342adc9f60c`. The architecture-review document commit is `c7ae36f1f10c2587d0810524aad02de059c48ba3`; this README handoff was subsequently committed separately. Fetch the PR API for the exact current head rather than treating the document commit as the branch head.
- The README update triggered fresh Test Suite, preflight, and Training Prototype Validation runs (IDs `44218597695`, `44218597785`, and `44218597762` respectively); their initial status was pending. Recheck their final conclusions on the current PR head before claiming validation passed.
- The Stage 2 checks passed on the previous head `fc1cfd0eaaa4424f66ea2368779510aa33845294`: Test Suite `44217854553`, preflight `44217854500`, Training Prototype Validation `44217854478`.
- Permanent project budget remains $0. Never enable billing, use paid trials, bypass quotas, or depend on paid services.
