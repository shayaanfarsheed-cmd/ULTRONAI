## Latest update — 2026-11-18 (owner-only cloud data library — implementation proposed)

- New work is on branch `feature/owner-data-library-sync`; it is not merged or deployed.
- Adds an owner-only Data Library view. The same private Supabase Storage bucket is used by every browser after signing in to the same verified owner account; Guest Mode cannot list, upload, download, or delete files.
- Browser library refresh is periodic while the dashboard is open and on tab visibility return. This is polling-based synchronization, not instant push notifications.
- Files are stored under the authenticated owner's UUID folder in a private `data-library` bucket. The proposed storage setup enforces SELECT/INSERT/UPDATE/DELETE ownership using `auth.uid()` and limits each file to 20 MiB.
- Uploading only stores bytes. Files are not executed or automatically added to training. No training was started.
- **Important deployment gate:** the storage bucket and RLS policies are SQL configuration only in this branch. They have not been applied to production Supabase. Do not enable production access until reviewed and separately approved.
- Tests and CI must pass on the pull request before merge. README is updated as part of every milestone.

---

## Latest update — 2026-11-18 (seed dataset scanner — PR in progress)

- Approved seed source: Hugging Face dataset `bkhtmm/openai-math-lemmas`, pinned to revision `d7056fd31c19fd1a0aed0a0bc3e99026d412b2ca`. The user downloaded the repository locally and confirmed 47 task folders.
- Stage 1 implementation is on branch `data/seed-dataset-scanner`: `ultron_seed_dataset.py`, `tests/test_seed_dataset.py`, and `docs/SEED_DATASET_IMPORT.md`.
- The scanner reads TOML/JSON metadata, inventories relative file paths, sizes, and SHA-256 hashes, and checks task/theorem consistency. It never executes dataset-provided scripts, Lean files, Dockerfiles, or shell commands.
- Scanner success means structure/metadata passed only. Proof status remains `not_checked`; dataset task metadata currently marks tasks `unvalidated`. Lean-kernel verification is a later stage.
- **PR #28 is open as a draft and is not merged**: https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/28. Latest code fix: `fe6e0a2218c3827f01f720f4e0de538f06ea32eb`. Initial CI found one failing test fixture (argument validation ran after a missing-folder check); the scanner now validates the argument first. A fresh CI run is required. The training-prototype workflow was cancelled during the earlier run. Do not merge without the user's explicit approval.
- No seed dataset source files, reference archives, or proof solutions are committed. The original local download remains unchanged.
- No model training has started. Do not start training as part of dataset import.

---

## Latest update — 2026-11-18

- **PR #27 merged** at `f1d8e074a2dfdf5e2718856760255bfc8e0e680d`. It adds the informational **How ULTRON Learns** dashboard view, responsive styling, and regression coverage. All three required PR workflows passed on exact head `a58eb2bbc84ef1d5530596c90b000ece7e0e5f47`.
- The new view explains the verified-data learning cycle, held-out evaluation, targeted improvement, and checkpoint promotion/rollback. It does not start training or add remote controls.
- **PR #25** remains open/unmerged: isolated local dummy-worker lifecycle prototype only; not a real trainer and not connected to the model.
- **PR #26** remains open/draft/unmerged: learning-system architecture documentation only.
- Main branch after PR #27: `f1d8e074a2dfdf5e2718856760255bfc8e0e680d`.
- Actual training has not started. Keep device pairing and remote training controls removed.

---

## Authoritative security update — 2026-11-18

- **PR #24 is merged** at `23f87a0a8176626781824d550341d6bed05d22d5`. All three PR checks passed on the exact reviewed PR head `95067c881d0a255da638d151e2f96f09870ba0f4`.
- The hosted dashboard is now read-only for training operations: no remote start/stop/pause/resume, switching, automatic-start, checkpoint-resume, server-status mutation, or manual usage writes. Status/history, provider links, and checkpoint verification/download remain read-only.
- The merge commit's GitHub Pages deployment completed successfully. A subsequent README-only handoff update is also being deployed; confirm its Pages workflow before declaring the very latest commit live.

- **Device pairing has been removed from the product at the owner's request.** The product will not pair remote devices, issue device credentials, or provide dashboard-to-device commands.
- The former heartbeat-only agent has been removed.
- Future training controls must be local to the device running training. The local user selects the RAM ceiling and operates Start/Stop there; the website cannot control another device.
- Training remains disabled. No checkpoints or training data are deleted.
- The hosted dashboard is now strictly read-only for training operations: no remote start/stop/pause/resume, switching, automatic-start, checkpoint-resume, server-status mutation, or manual usage writes. Checkpoint verification/download and status/history display remain read-only.
- The old Supabase pairing tables are retained inert for auditability; the production Edge Function has been replaced with a fail-closed HTTP 410 response. No direct browser grants are to be added.
- PR #22 (pairing security tests) is closed and obsolete. PR #23 was reviewed and merged on 2026-11-18; merge commit: `acd9b8a20aac4552592a1b3fa7b72b9d2513bf2c`. All three required PR workflows passed on its exact head.
- Local training architecture and failure-handling plan: docs/LOCAL_AGENT_ARCHITECTURE.md.

---

# ULTRONAI — Project status and handoff

**Repository:** [shayaanfarsheed-cmd/ULTRONAI](https://github.com/shayaanfarsheed-cmd/ULTRONAI)  
**Dashboard:** [GitHub Pages](https://shayaanfarsheed-cmd.github.io/ULTRONAI/)  
**Main branch:** `main`  
**Latest merged work:** PR #24 — make hosted dashboard read-only for training operations, merged at `23f87a0a8176626781824d550341d6bed05d22d5`.

## Current priorities

1. Finish and validate the dashboard/frontend before starting any model training.
2. Test owner authentication and Guest Mode against the deployed website.
3. Keep the website usable on iPad/iPhone, Android, and desktop browsers.
4. Keep all work within the $0 budget.

## Recently merged work

- **PR #14 — [Improve dashboard mobile accessibility and safe-area layout](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/14)**  
  Merged on 2026-11-18 at `b4f7209f4c9572f03e1fb221e9304ba0e211ba88`. Added keyboard skip navigation, selected-navigation semantics, visible focus, iOS safe-area spacing, responsive navigation refinements, reduced-motion support, landscape insets, touch targets, and regression coverage.
- **PR #15 — [Update README after PR #14 merge](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/15)**  
  Merged on 2026-11-18 at `1de739ba0f15dd9d2fda3ba0dd503baeb801c15d`.
- **PR #16 — [Configure verified owner authentication](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/16)**  
  Merged on 2026-11-18 at `7b0dc262a2319c00253f106b9122efe13a388063`. Configured the verified owner Auth UUID and public Supabase publishable key in `dashboard/config.js`, and updated regression tests to require valid configuration values. All three required PR workflows passed on the exact final head: preflight, Test Suite, and Training Prototype Validation.
- GitHub Pages deployment after PR #16 still needs to be verified. Owner sign-in and Guest Mode have not yet been manually tested on the deployed site.
- **Real-device compatibility testing is still outstanding.** Automated CI does not prove iPad/iPhone, Android, or desktop browser behavior.

## Product and security constraints

- Website first; no real training until the user explicitly approves it.
- $0 budget. No paid APIs, paid trials, billing setup, Kaggle, or phone-number-dependent setup.
- No external AI inference APIs, pretrained weights, existing models, or externally generated training data. ULTRON's model, data generator, and training code are independently implemented.
- No production Supabase schema, RLS, grants, storage, Edge Function, or secret changes without separate explicit approval.
- Never put privileged keys, service-role secrets, or passwords in browser code, notebooks, commits, or logs.
- The Supabase publishable key in `dashboard/config.js` is designed for public browser use; never substitute a secret/service-role key.
- Guest Mode is the public default. Owner sign-in is a single owner account; public self-registration is disabled.
- The owner Auth user has been created and email-confirmed in Supabase. Its UUID and the project's publishable key are now configured in the merged main branch. The user must test sign-in using their email/password directly in the website; never ask them to paste the password into chat.
- Frontend UUID checks and browser session storage are not backend authorization or secure credential storage. Private operations require server-side authorization and RLS.
- Current inspected database state: RLS is enabled on all six public memory tables and the three `training_api` tables. Owner-scoped policies were present for the inspected memory/training records; Storage has an owner-folder SELECT policy for the `checkpoints` bucket. The browser must still be tested against these policies with both owner and Guest Mode.
- Supabase Security Advisor reports **Leaked Password Protection Disabled**. Enable it in Supabase Auth password/security settings when ready; no production setting was changed during this work.
- No device pairing, agent installation, provider jobs, or live training without separate explicit approval.
- The RAM slider is a local preference only. It does not enforce a process or operating-system memory cap.

## Model and training status

- From-scratch decoder-only Transformer with approximately 4.04 million trainable parameters, character-level tokenization, 78-character vocabulary, 5 layers, embedding size 256, 8 attention heads, and context length 192 characters.
- Randomly initialized; no pretrained weights.
- Own data generator covers 14 topic areas; an independent arithmetic verifier exists.
- Automated smoke tests validate implementation mechanics, not broad mathematical competence.
- **Actual model training has not started.** Resolve the older 1024-token context target before changing architecture.

## Latest implementation notes

- PR #12 added bounded checkpoint metadata/file handling, concurrency controls, manifest checks, chart scheduling safeguards, and single-flight session refresh.
- PR #13 added incremental checkpoint response streaming, early cancellation at the configured byte cap, declared/actual length checks, fail-closed handling without streaming, strict manifest step validation, and regression tests.
- The stream reader bounds the retained response buffer, but temporary buffer growth can hold old and new allocations; it is not a hard total browser-process memory cap.
- PR #14 contains frontend accessibility and responsive-layout changes only; no real-device compatibility test has been performed.
- PR #16 configures owner authentication but does not provision devices, start training, or enable AutoStart.

## Required validation

- After PR #16 deployment, open the GitHub Pages dashboard and test owner sign-in using the owner's email/password directly in the sign-in dialog.
- Confirm Guest Mode cannot read private records, and owner mode can access only the configured owner's records. Inspect any auth, RLS, or Storage failures without weakening access controls.
- Confirm sign-out returns to Guest Mode and clears private browser state.
- Test actual iPad/iPadOS Safari and Chrome, iPhone, Android, and desktop browsers, including narrow/wide layouts, refresh, interrupted network, and keyboard/screen-reader navigation. Do not claim device compatibility unless tested on those devices.

## Latest merged change — PR #24

- PR #24 merged at `23f87a0a8176626781824d550341d6bed05d22d5` after all three required checks passed on the exact reviewed PR head.
- The hosted dashboard no longer sends training-control writes or offers remote training controls, checkpoint resume, server-status edits, or manual usage writes. Read-only status/history, provider links, and checkpoint verification/download remain.
- RAM selection remains a browser preference only; it does not enforce a memory cap.
- Merge-triggered `main` checks and GitHub Pages deployment must be verified before claiming the live site is updated.

## Next steps for the next session

1. Verify the merge-triggered GitHub Pages deployment for `23f87a0a8176626781824d550341d6bed05d22d5`, then inspect the live dashboard for absence of all remote training controls and confirm status/checkpoint views remain read-only.
2. Test owner authentication and Guest Mode in the deployed site; verify private records remain protected.
3. Verify the production `device-control` Edge Function still fails closed with HTTP 410; direct HTTP invocation was not available during the earlier retirement check. Keep historical pairing tables inert and private.
4. Continue iPad/browser frontend testing before runtime work. Then implement a local-only dummy-worker state machine with explicit local Start/Stop, verified RAM enforcement, safe checkpointing, and regression tests. No remote device control.
5. Keep real training disabled. Do not start it until the local runtime is implemented, validated, and the user separately approves it.

<!-- Historical next steps from the previous architecture are retained below for audit context. -->

1. Verify the GitHub Pages deployment for merge commit `7b0dc262a2319c00253f106b9122efe13a388063`.
2. Test owner sign-in and Guest Mode in the deployed website; report the exact UI error if sign-in fails, but never share the password.
3. Verify private memory and checkpoint requests are correctly restricted by Supabase RLS and Storage policies.
4. Address the Supabase leaked-password-protection warning through the Supabase dashboard when authorized.
5. Continue dashboard UX and real-device testing. Do not start real training until the user explicitly approves it.


## Retired device-pairing work package (historical record — superseded by PR #23)

All earlier pairing implementation notes later in this README are historical only. They do not describe the current product or authorize restoring pairing, device agents, remote commands, or training.

- Device pairing was implemented and deployed temporarily, then retired at the owner's request in November 2026.
- The repository no longer contains the pairing UI/API client or Python heartbeat agent. The production Edge Function now fails closed with HTTP 410.
- Historical migration files and private database tables are retained inert for auditability; no browser grants or new callers are allowed.
- No remote device command channel will be built. Future RAM enforcement and Start/Stop controls must run locally beside the training process.
- Before production deployment, add edge/gateway per-IP throttling and disposable-project integration tests for concurrent redemption, expiry, attempt lockout, owner isolation, revocation, and secret redaction.


## Device pairing — PR #18 merged

- [Build secure device pairing control plane](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/18) merged on 2026-11-18 at `1f0ff3f6cdd7d75d23e5fbd594bb3b4d5627ce7b`.
- Implements owner-only pairing challenge creation, one-time redemption, hashed device credentials, device registry/revocation, and heartbeat endpoint.
- Security review correction: Edge Function now checks the verified Auth user against `ULTRON_OWNER_USER_ID`; the database consume function uses `SECURITY INVOKER` and is executable only by service_role; a newly issued code invalidates older outstanding challenges; capability payloads must be JSON objects within the size limit.
- Pairing dashboard stays disabled unless `window.ULTRON_CONFIG.deviceControlEnabled === true`.
- Historical note superseded by the production deployment update below: the migration and Edge Function have now been deployed. The custom `ULTRON_OWNER_USER_ID` secret remains to be configured manually in Supabase Dashboard; integration tests and dashboard feature-flag enablement remain blocked until that step is complete.
- A compatible OS-level agent and disposable-project integration tests are not complete. The iPad browser cannot run this background agent; it can only act as the owner dashboard/monitor unless a native iPad app is later built.
- Production pairing schema and Edge Function are now deployed following explicit user approval. No custom owner secret has been added, no device has been paired, no remote commands have been enabled, and no training has started.


- Added `agents/device_agent.py`: minimal Python heartbeat-only agent for Linux/macOS/Windows/server environments. It prompts for the one-time challenge, holds the device token in memory, never prints or writes it to disk, and can resume using a provider secret named `ULTRON_DEVICE_TOKEN`. It does not execute remote commands or training. iPad remains the owner dashboard/monitor; iPadOS agent support would require a native application.


## Historical handoff — after PR #18 (superseded by the updates below)

1. Historical action: verify GitHub Pages deployment for merge commit `1f0ff3f6cdd7d75d23e5fbd594bb3b4d5627ce7b` (completed; later deployments are recorded above).
2. Keep `deviceControlEnabled` false until the owner secret is configured and integration/security tests pass.
3. The user has now reported configuring the custom Edge Function secret. Do not ask them to share its value; connected tools cannot read it back.
4. Run disposable-project integration tests if a no-cost disposable project is available; do not create a paid project or run destructive tests against production.
5. After tests pass and a separate reviewed feature-flag PR is merged, pair a supported Linux/macOS/Windows cloud worker using the Python heartbeat agent. The iPad remains the owner dashboard and monitor; it cannot host the persistent Python agent.
6. Device pairing only records a device and heartbeat. Do not start training or accept remote commands until a separate secure job-control design is approved.



## Latest validation update — 2026-11-18

- User confirmed that the Supabase Edge Function secret `ULTRON_OWNER_USER_ID` has been configured. The secret value is not retrievable through the connected tooling; record this as user-reported, not independently value-verified.
- Read-only verification confirms the Supabase project is healthy, `device-control` is ACTIVE (version 2), the three pairing tables exist, RLS is enabled, direct `anon`/`authenticated` SELECT is denied, and both RPC functions are `SECURITY INVOKER` with execute permission limited to `service_role`.
- Pairing UI remains disabled (`deviceControlEnabled` is not enabled). No device is paired and no training has started.
- Dashboard copy was corrected in `dashboard/index.html`: it now states that the Supabase migration and Edge Function are deployed and the owner secret is user-confirmed; pairing remains disabled only for the outstanding integration/security test gate. The compatible heartbeat agent exists, but no device has been paired.
- Remaining gate: safe integration tests for challenge concurrency/single-use, expiry, five-attempt lockout, owner isolation, revocation, and per-IP rate limits. Do not run destructive tests against production or create a paid staging project. If a disposable free environment is unavailable, document that limitation and keep the feature flag off.


## Production deployment update — 2026-11-18

- User explicitly authorized applying the production pairing migration and deploying the `device-control` Edge Function to the existing Supabase project.
- Applied migration `device_pairing_control_plane` (database version `20261118103221`). It created `ultron_devices`, `ultron_pairing_challenges`, and `ultron_pairing_rate_limits`; RLS is enabled and direct `anon`/`authenticated` table privileges are revoked. Both RPC functions are `SECURITY INVOKER` and executable only by `service_role`.
- Deployed Edge Function `device-control`, version 1, status ACTIVE. Gateway JWT verification is disabled because the function implements its own verified-owner Auth check for owner routes and device-token authentication for heartbeat; unauthenticated access to owner routes fails closed.
- Verified migration history, active function deployment, RLS state, table grants, and RPC execute grants through read-only checks.
- Supabase Security Advisor reports informational `rls_enabled_no_policy` findings for the three pairing tables. This is intentional: no direct client table access is granted; the Edge Function uses the service role after its own authorization checks. Advisor also reports the pre-existing Auth leaked-password-protection warning.
- Supabase Performance Advisor reported unused indexes immediately after creation and several pre-existing unindexed foreign keys; these are informational and not a reason to expose the pairing tables.
- **Owner secret update (2026-11-18):** the user reports configuring the Edge Function secret `ULTRON_OWNER_USER_ID` in Supabase Dashboard. Secret values are intentionally not readable through the connected tools, so its contents cannot be independently inspected. The function fails closed if the value is missing or does not match the verified owner Auth user.
- **Still disabled:** dashboard feature flag `deviceControlEnabled`; no device is paired; no device commands or training are enabled.
- **Verified after the user's secret-configuration confirmation:** Supabase project is `ACTIVE_HEALTHY`; `device-control` is ACTIVE (version 2); all three pairing tables exist with RLS enabled; `anon` and `authenticated` have no direct table SELECT privileges; both RPC functions are `SECURITY INVOKER` and executable only by `service_role`.
- **Testing limitation:** integration tests for concurrent redemption, owner isolation, expiry, attempt lockout, revocation, and rate-limit windows have not yet run against a disposable Supabase project. Do not claim production pairing is fully validated. Do not create a billable staging project; keep within the $0 budget.
- Next action: complete a no-cost integration-validation plan without destructive tests against production. Only then prepare a separate reviewed PR to enable the dashboard control.


## Current project status — 2026-11-18 (supersedes earlier pairing plans)

- **Device pairing is permanently retired for this design.** Do not re-enable pairing, device agents, device registries, remote command channels, or remote start/stop/pause/resume controls. The retired `device-control` endpoint fails closed with HTTP 410; historical private database objects are retained inert for auditability.
- **PR #23 is merged** (merge commit `acd9b8a20aac4552592a1b3fa7b72b9d2513bf2c`).
- **PR #24 is open**: hosted dashboard training operations are being made read-only. It removes dashboard training-control mutations while retaining permitted read-only status/history and checkpoint verification/download. The RAM slider remains a local browser preference only and does not enforce a memory cap.
- PR #24's initial CI runs exposed one stale assertion in `tests/test_dashboard.py` that expected the removed `autoStartToggle` handler. The test now verifies that the obsolete control is absent from both dashboard HTML and JavaScript, while confirming guest messaging says training remains disabled. Re-run all required CI checks against the new PR head before considering merge.
- **No real training has started.** After PR #24 passes review and merges, verify GitHub Pages deployment and the live dashboard. Then implement a local-only dummy-worker runtime with explicit local Start/Stop, verified resource-limit semantics, safe checkpointing, and regression tests. Do not begin real model training until that prototype is validated and the user separately approves it.
- This status section supersedes older README passages that describe enabling device pairing or remotely controlling a worker; those are obsolete and must not be followed.
