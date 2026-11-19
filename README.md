# Latest update — 2026-11-19 (Conversational reasoning architecture started)

- PR work is on branch `architecture/conversational-reasoning-foundation`; it is not merged.
- Added `docs/CONVERSATIONAL_REASONING_ARCHITECTURE.md`, defining a mathematics-first conversational assistant with request routing, structured problem parsing, explicit solution plans, independent verification, bounded repair/abstention, evidence-based mistake diagnosis, adaptive teaching, concept dependencies and user-controlled memory.
- Current baseline is accurately distinguished: the 4,038,478-parameter transformer is randomly initialized; the existing Math Agent is deterministic/rule-based and supports restricted formats. The Math Agent is not the neural model.
- The target is to adopt useful interaction/reliability qualities associated with GPT/Astra/Claude, not to clone proprietary systems or claim equivalent general intelligence. The 3–5M parameter target is a constrained math-specialist goal.
- Staged delivery: conversational math shell → structured reasoning kernel → mistake diagnosis/teaching → neural model/tokenizer/context improvements → possible broader assistant scope.
- No code/model weights/training data/database configuration changed in this architecture-only stage. No real training started; no external AI APIs, pretrained weights, paid services or externally generated training data are permitted.
- Next: implement Stage 1 as a responsive multi-turn mathematics chat shell, routing supported prompts to the existing deterministic solver with bounded session context, clarification and explicit unsupported-input handling. Add browser regression tests and keep the neural model status honest.
- Keep README updated at every milestone. Do not merge without explicit owner approval.

---

## Current provider decision — 2026-11-19

- **GitHub Actions CPU is the sole remote training provider** and the dashboard's only remote Start/Stop target.
- Google Colab remains manual-only; it is not remotely launched or automatically controlled.
- GitHub Actions CPU is the only remote training provider. Google Colab is manual-only; Hugging Face Hub is optional checkpoint storage.
- Hugging Face Hub remains optional private checkpoint/artifact storage only; Hugging Face Spaces compute is not used.
- GitHub Actions CPU training remains owner-authenticated and owner-confirmed. The workflow requires the configured private Supabase credentials, performs preflight and a read-only backend connection test before training, and relies on the existing lease/checkpoint protections.
- No training has started. Do not start a real training run until the owner explicitly approves it. No production Supabase function or secrets were changed by this branch update.
- **Current PR #52 remains open and unmerged**, stacked on PR #51, which is stacked on PR #50. Merge only in dependency order after review and explicit owner approval.
- README is the handoff source of truth. Update this section and the next-step checklist at each milestone.

---

## Latest provider update — 2026-11-19

- GitHub Actions CPU is the only remote training provider; Google Colab is manual-only.
- The provider registry and dashboard expose GitHub Actions CPU for remote training; Google Colab remains a manual-only option.
- Hugging Face Hub remains optional private checkpoint/artifact storage only.
- CI for this provider-removal revision is pending. No training has started and no production Supabase function or secret was changed.

---

## Latest update — 2026-11-19 (Frozen Math Agent evaluation merged)

- PR #42 merged at `172685831fedea21de2edc1982099fbcd83fdd0a`. The later README-only correction PR #43 merged at `803acb0bff49401a11673c04fd80d3ba827df623`.
- All three merge-triggered checks passed on the exact main commit: ULTRON Test Suite (run `44443811629`), ULTRON preflight tests (run `44443811610`), and GitHub Pages build/deployment (run `44443810802`). The PR checks also passed before merge.
- The Math Agent now has a separate browser action that scores the frozen `ultron-heldout-foundation-v1` test split. It computes each answer before comparing the expected label and requires the independent verifier to agree.
- Automated regression coverage confirms all 14 pilot cases pass and rejects altered labels, duplicate IDs, non-test samples, and unfrozen data. Fourteen examples are a wiring/pilot check, not statistically meaningful evidence of broad mathematical ability.
- The held-out score is separate from the generated throughput benchmark and is never sent to training or curriculum selection.
- No neural training, model-weight updates, external APIs, Supabase changes, or production configuration changes were made. Training remains disabled.
- Next step: manually test the deployed Math Agent on iPad Safari (solve, held-out evaluation, start/stop/reset, backgrounding, and narrow-screen layout). Do not claim real-device compatibility until that test is completed.

---

## Latest update — 2026-11-19 (Browser Math Agent merged)

- PR #41 merged successfully at `8776a7cd73aee91fa1a98c8c59a1457b94d0196a`; final reviewed PR head was `ef3053bc28d4cd42dd0ee26cc621875c58efcec8`.
- All three required PR workflows passed on that exact final head:
  - ULTRON Test Suite — run `44443194723` (success; includes static JavaScript validation and the browser Math Agent Node tests).
  - ULTRON Training Prototype Validation — run `44443194753` (success).
  - ULTRON preflight tests — run `44443194806` (success).
- Adds `dashboard/math-agent.js`, a browser-native deterministic solver for all 14 foundation topics, with exact integer/fraction/decimal arithmetic, inspectable knowledge summaries, and worked steps. The answer checker recomputes results using its own arithmetic helpers rather than calling the solver helpers.
- Adds the public Math Agent page at `dashboard/`: choose a topic, read the accepted question format, load an example, solve, and independently verify. The benchmark has Start/Stop/Reset controls, a 5,000-question hard cap, small yielding batches, and stops when the page is backgrounded or another dashboard view is selected.
- Displays overall questions/second, verified solutions/second, accuracy, completed count, and per-topic generated/verified accuracy.
- Regression tests cover every topic, generated question formats, invalid and oversized input, deliberately wrong answers, and exact fraction/decimal arithmetic. The existing full suite and all three required workflows passed.
- This is a deterministic rule-based browser agent, not the neural model. It does not use external AI APIs, pretrained weights, uploaded files, or training. It does not update model weights. Neural-model training remains disabled.
- iPad layout is responsive by design, but a manual Safari/iPad interaction test is still outstanding; automated CI cannot replace a real-device check.
- Next frontend milestone: review and test the Math Agent in the deployed GitHub Pages site, then continue the remaining frontend gaps. Do not start training until the user explicitly approves it.

## Latest update — 2026-11-19 (ULTRON Math Agent merged)

- PR #40 merged successfully at `f5b366b5ecff7026e8bce9257ac53e3af81778d0`; final reviewed PR head was `ac9ef21f19f6a65afea5ed0bbe551d0d5f54dc67`.
- All three required workflows passed on that exact final PR head:
  - ULTRON Test Suite — run `44442061963` (success; 169 unit tests passed).
  - ULTRON Training Prototype Validation — run `44442061790` (success).
  - ULTRON preflight tests — run `44442061897` (success).
- Adds `ultron_agent.py`, a deterministic, rule-based math agent for all 14 supported foundation topics. It accepts only topic + question, computes its own answer and worked steps, then sends those results to the separate `ultron_verify` verifier. Generator-provided answers and steps are not used by the solver.
- Includes an inspectable mathematical knowledge summary for each topic (concept, rule/formula, and method). Each sample solution includes the summary and working.
- Default CLI benchmark: `python ultron_agent.py`. It runs for one second by default, up to 50,000 questions, and reports questions/second, independently verified correct solutions/second, accuracy, failures, and per-topic metrics. Example: `python ultron_agent.py --count 50000 --seconds 1`.
- Direct question input is limited to 1,000 characters. Unsupported question formats are rejected rather than guessed. The agent is not the randomly initialized neural model and does not update model weights.
- No website, database, production configuration, or model weights changed. No actual model training was started. Training-prototype CI uses a bounded smoke test only.
- Next isolated step: implement the user-facing ULTRON solve/benchmark interface and connect it to this agent, keeping the website/iPad frontend usable and training disabled.

## Latest update — 2026-11-19 (Stage 2 read-only evaluation runner merged)

- PR #39 merged successfully at `b5bcd25f1130276cdf614161be46b2cf5cd355ce`; final PR head was `6d21e32d3d2e75e7e27da97e0e7fff8f726cb0c3`.
- All three required workflows passed on that exact head:
  - ULTRON Test Suite — run `44438882204` (success).
  - ULTRON preflight tests — run `44438882182` (success).
  - ULTRON Training Prototype Validation — run `44438882236` (success).
- Adds `ultron_evaluation.py`, a read-only scorer for explicit `sample_id -> predicted answer` mappings against the canonical frozen `ultron-heldout-foundation-v1` fixture.
- Reports overall, per-topic, and per-difficulty accuracy; missing/incorrect answer categories; evaluator/dataset versions; and a deterministic SHA-256 fingerprint of the canonical prediction mapping. Mathematical answer content is exact-match after whitespace normalization.
- The runner requires the exact canonical fixture, frozen identity, unique sample IDs/questions, and reserved `test` split. Unknown prediction IDs and non-string predictions are rejected. It cannot silently score a modified or partial fixture.
- Example: `python ultron_evaluation.py --predictions predictions.json --output report.json --model-label checkpoint-001`. The input JSON maps fixture sample IDs to model-produced answer strings.
- Regression tests cover perfect/partial predictions, failure categories, normalization, unknown IDs, invalid values, deterministic reports, dataset immutability, and rejection of modified/partial evaluation fixtures.
- This is a scoring utility only. It does not load a model or run inference, change weights/checkpoints, feed evaluation examples into training/curriculum, or start training. The 14-case pilot remains too small to establish broad mathematical competence.
- No website, database, or production behavior changed. No real model training was started.
- Next isolated step: expand the frozen held-out cases with balanced topics and difficulty coverage. Keep the evaluation split excluded from training and curriculum selection, and merge that step before moving on.

## Latest update — 2026-11-19 (Stage 2 held-out evaluation pilot merged)

- PR #38 merged successfully at `efe67f98f09046458fca8d4e4760ed0c85be5ccd`.
- All three required CI workflows passed on PR head `480b04a5c7cc8b9e4226aa8c2dd610b7b9f9f13f`: ULTRON Test Suite, ULTRON Training Prototype Validation, and ULTRON preflight tests.
- The merged change adds a frozen, hand-authored pilot set with one difficulty-1 example for each of the 14 supported topics, plus regression tests for independent-verifier validity, unique questions/sample IDs, and isolation in the existing hash-based `test` split.
- This 14-example pilot is a wiring/safety check, not a statistically meaningful accuracy benchmark. Do not claim model competence from it.
- No model, training loop, weights, checkpoint, production database, or website behavior was changed. No training was started.
- Next incremental step: add a read-only evaluation runner with deterministic scoring and topic/difficulty metrics, then validate it with broader held-out cases and regression coverage. Keep evaluation data out of training and curriculum selection.
- Workflow rule: finish, test, review, and merge each isolated step before starting the next.

## Latest update — 2026-11-19 (PR #36 merged; evaluation is next)

- PR #36 merged successfully at `d2fbcad6839371655e3ffb8d7e65e363d91b634e`.
- All three required PR workflows passed on head `439752f876c7c09f56cf5cd6fcafd97183e00875`: ULTRON Test Suite, ULTRON Training Prototype Validation, and ULTRON preflight tests.
- The merge adds a bounded, deterministic generation-and-verification dry run. It does not persist datasets, change model weights, invoke a trainer, or start training. Follow-up review found that the dry-run duplicated split logic and used generation-index fallback for candidates without questions; this could misclassify failed candidates in split-specific reports.
- Both `ultron_data.py` and `ultron_self_learning.py` now use one shared `question_split()` function. A missing/invalid question is reported as unassigned and is never assigned by sample index.
- Generator failures are reported separately from split-specific candidate rejections. Only the dedicated `InvalidGeneratedExampleError` is counted as an expected invalid candidate; unexpected generator and verifier programming errors propagate instead of being silently swallowed.
- Candidate topic, difficulty and sample-index metadata are checked against the generation request. Input types and callable dependencies are validated.
- The verifier now checks the generated solution-step sequence against steps independently reconstructed from the question; correct final answers with corrupted intermediate steps are rejected.
- Regression tests now compare dry-run output directly with the existing dataset generator for train, validation and test splits; also cover missing questions, metadata mismatch, and unexpected exceptions.
- The verifier remains the same verifier module used by the generator; the dry-run's second call is a boundary check for custom/injected generators, not a second independent verifier implementation.
- No datasets are persisted, no model weights are changed, and no training is started. The dry-run merge is validated; it does not establish that the neural model has learned or that its mathematical accuracy has improved.

---



- PR #35 merged at `d8dcdd72b95c94538985132cb055cf227b69eb26`; its three required CI workflows passed and the GitHub Pages build/deployment workflow completed successfully.
- Data Library limits on `main`: 50,000 files per upload, 20 MiB per file, 5,000 MiB (5 GiB) total per batch, and 12 path levels. Uploads remain owner-only and storage-only.
- PR #36 is merged at `d2fbcad6839371655e3ffb8d7e65e363d91b634e`; all three required CI workflows passed on its exact head. It adds `ultron_self_learning.py`, a bounded deterministic generation-and-verification dry run, with regression tests for deterministic output, split isolation, corrupted examples, generator failures and safety boundaries.
- The learning architecture is documented in `docs/SELF_LEARNING_ARCHITECTURE.md`: verifier feedback, curated synthetic data, targeted model updates, persistent memory/retrieval, test-time self-verification, anti-forgetting replay, held-out evaluation and anti-collapse/reward-hacking checks.
- Training remains disabled in this stage. The dry run does not write datasets, modify weights or invoke the trainer. No LoRA/adapters are assumed; consider them only after a trained baseline exists and the model architecture supports them.
- Next gate: build a fixed held-out evaluation suite with topic/difficulty breakdowns, baseline metrics, deterministic scoring and regression thresholds. Keep evaluation examples out of any training data. Then add inspectable memory/retrieval and answer-time verification; only later propose bounded training for explicit owner approval.

---

## Latest update — 2026-11-18 (owner-only cloud data library — implementation proposed)

- New work is on branch `feature/owner-data-library-sync`; it is not merged or deployed.
- Adds an owner-only Data Library view. The same private Supabase Storage bucket is used by every browser after signing in to the same verified owner account; Guest Mode cannot list, upload, download, or delete files.
- Browser library refresh is periodic while the dashboard is open and on tab visibility return. This is polling-based synchronization, not instant push notifications.
- Files are stored under the authenticated owner's UUID folder in a private `data-library` bucket. The proposed storage setup enforces SELECT/INSERT/UPDATE/DELETE ownership using `auth.uid()` and limits each file to 20 MiB.
- Uploading only stores bytes. Files are not executed or automatically added to training. No training was started.
- **Important deployment gate:** the storage bucket and RLS policies are SQL configuration only in this branch. They have not been applied to production Supabase. Do not enable production access until reviewed and separately approved.
- Tests and CI must pass on the pull request before merge. README is updated as part of every milestone.

---

## Seed dataset scanner status — 2026-11-18

- PR #28 merged at `caac7e37c935df0ddd0e18d66f828f8675d47b69`. The scanner inventories the approved local seed dataset; it does not validate Lean proofs or execute source files.
- PR #29 corrects earlier stale README status and remains separate from the data-library proposal.
- The original 47-task source dataset remains local; no raw dataset files have been committed. No training has started.

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
- $0 budget. No paid APIs, paid trials, billing setup, or phone-number-dependent setup.
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


## Adaptive learning and GitHub Actions optimization — PR in progress (2026-11-19)

- Added adaptive topic-weighted practice: held-out per-topic accuracy updates the training stream's sampling priorities. Weak topics receive more practice while mastered topics remain in the epoch, avoiding permanent forgetting.
- Sampling uses a weighted permutation without replacement, so examples are not duplicated within an epoch. Topic scores and the data order are included in the existing checkpointed batch-stream state so recovery preserves the learning strategy.
- GitHub Actions CPU runtime is tuned to two PyTorch CPU threads for the standard hosted runner; pip dependency caching is enabled.
- Fixed the stale guided-switch regression expectation: when the current worker is Colab, the next guided handoff correctly targets GitHub Actions CPU; Colab remains a manual-only runtime.
- New regression tests cover weak-topic prioritization, no duplicate samples, invalid metric rejection, and exact sampler-state recovery.
- These mechanisms are learning heuristics, not evidence of human consciousness or human-equivalent reasoning. They improve practice allocation and retention checks; held-out evaluation remains the mastery gate.
- Real training has not been started. This PR is stacked on PR #52 and is not merged. Run the full test suite and all required CI workflows before merging.
- Next: inspect CI logs on the latest PR head, fix every failure, review the sampler/checkpoint integration, then verify the dashboard's training controls remain owner-gated. Do not start a real training run during validation.

## Current project status — 2026-11-18 (supersedes earlier pairing plans)

- **Device pairing is permanently retired for this design.** Do not re-enable pairing, device agents, device registries, remote command channels, or remote start/stop/pause/resume controls. The retired `device-control` endpoint fails closed with HTTP 410; historical private database objects are retained inert for auditability.
- **PR #23 is merged** (merge commit `acd9b8a20aac4552592a1b3fa7b72b9d2513bf2c`).
- **PR #24 is open**: hosted dashboard training operations are being made read-only. It removes dashboard training-control mutations while retaining permitted read-only status/history and checkpoint verification/download. The RAM slider remains a local browser preference only and does not enforce a memory cap.
- PR #24's initial CI runs exposed one stale assertion in `tests/test_dashboard.py` that expected the removed `autoStartToggle` handler. The test now verifies that the obsolete control is absent from both dashboard HTML and JavaScript, while confirming guest messaging says training remains disabled. Re-run all required CI checks against the new PR head before considering merge.
- **No real training has started.** After PR #24 passes review and merges, verify GitHub Pages deployment and the live dashboard. Then implement a local-only dummy-worker runtime with explicit local Start/Stop, verified resource-limit semantics, safe checkpointing, and regression tests. Do not begin real model training until that prototype is validated and the user separately approves it.
- This status section supersedes older README passages that describe enabling device pairing or remotely controlling a worker; those are obsolete and must not be followed.


## Ask ULTRON — document-grounded questions (in progress)

- A separate Ask ULTRON dashboard view is being added on branch `feature/ask-ultron-data-qa`.
- The first version searches owner-only files in the private `data-library` bucket after verifying the owner session. It retrieves text passages and displays matching evidence with source filenames.
- Supported text formats: TXT, Markdown, CSV, JSON, Lean, TOML, YAML, Python, JavaScript, TypeScript, HTML, XML, and LOG. PDF and other binary formats are not supported in this first version.
- Safety limits: maximum 5 MiB per file and 15 MiB total downloaded per search. Uploaded content is decoded as UTF-8 text only; it is never executed.
- This is deterministic local retrieval, not a trained ULTRON neural answer model. It does not use an external AI API, start training, or invent a synthesized answer. It reports relevant source passages or says no evidence was found.
- No Supabase schema or production Storage policy changes are part of this feature.
- Keep the feature owner-only. Guests must not list, download, or search private files.

## Folder uploads

- Data Library supports individual files and browser directory selection.
- Directory uploads preserve each file relative path under the verified owner private Storage folder; uploads run sequentially with file-count progress.
- Limits: 20 MiB per file, 50,000 files per upload, 5,000 MiB (5 GiB) per batch, maximum 12 path levels. Library listing is paginated in batches of 500 to support large folders.
- Library browsing is recursive; download, delete and Ask ULTRON use the complete relative path.
- Uploading is storage only: no execution, Lean proof validation, training-dataset creation, or training start. Ask ULTRON searches only its supported UTF-8 text formats.
- Directory picker support depends on the browser; multi-file selection is the fallback.


### Next step

- Validate the 50,000-file Data Library cap and paginated recursive listing in CI before merging the change. The 5,000 MiB (5 GiB) per-batch and 20 MiB per-file limits are enforced.


## Data Library deletion controls — in progress

- Individual file deletion remains available with an explicit confirmation.
- Bulk deletion allows the owner to select multiple files and permanently remove them from the private Storage bucket.
- Folder deletion removes every currently listed object beneath that relative folder path; requests are split into batches of at most 1,000 object paths.
- All delete operations require the verified owner session, confirm before deletion, and refresh the shared cloud listing after success. Other signed-in browsers see the change on their next refresh (normally within 20 seconds).
- Guests cannot select or delete private files. Deletion is permanent; there is no recycle bin or restore function.
- Validate the deletion regression tests and deployed behavior before treating these controls as live.


## Training reliability hardening — PR #47 merged

- PR #47 merged to `main` on 2026-11-19 (merge commit `1f80f1b473d4ecb18fd9feeb13892d3dc5a87a1b`).
- A training session must not report a safe pause or handoff unless the latest checkpoint is durably committed to primary Supabase Storage or independently verified in the configured secondary backup.
- If neither durable path succeeds, the worker stops training and deliberately does not release its lease; the lease expires naturally so another worker cannot race ahead from stale progress. The local checkpoint is diagnostic/recovery material only and is not treated as durable across provider runtime resets.
- Worker-local checkpoint directories are temporary and must never be mistaken for cross-session persistence. Supabase remains the required primary durable store; Hugging Face Hub is optional secondary backup storage only.
- The regression test covers failure to commit the primary checkpoint when no secondary backup is configured. Real training remains disabled.


## Checkpoint recovery hardening — PR in progress

- The isolated recovery command uses CUDA when available and CPU otherwise. CUDA precision is selected from device capability: BF16 when supported, otherwise FP16 with GradScaler.
- The test saves and restores GradScaler state when FP16 is active, and compares the next update from a fresh runtime with an uninterrupted reference on the same device and precision.
- CPU-only CI exercises the full-precision fallback. An optional CUDA test runs in GPU-enabled CI and is skipped on CPU-only runners.
- Fake-Storage regression tests inject interrupted component upload and interrupted fresh-runtime download, then verify that only the test's own temporary prefix is cleaned.
- Fake Storage cannot prove real Supabase permissions, network behavior, or live bucket cleanup. The GitHub Actions/Supabase checkpoint round trip remains a separate validation requirement.
- The command does not call the training-status API, acquire a production lease, modify production run pointers, or start real training.
- Never paste or print provider secret values. Checkpoint recovery tests use isolated temporary storage; live provider recovery must be validated separately.

### Next steps

1. Run the full repository test suite and inspect all required GitHub checks.
2. Review the exact merged code after CI passes.
3. Treat live GitHub Actions/Supabase recovery as unverified until the isolated command succeeds against the actual private bucket.
4. Keep real training disabled until live recovery and the separate readiness review pass, followed by explicit user approval.


## iPad owner launch control — implementation in progress (2026-11-19)

- Added a dedicated owner-only Training Control view to the static dashboard. The iPad is the control console; compute runs on the selected provider, not on the iPad.
- The first remotely launchable target is GitHub Actions CPU, through the existing `cpu-training.yml` workflow and the `ultron-cpu-start` repository-dispatch event.
- GitHub Actions CPU is the only remote training provider. Google Colab remains manual-only.
- The new `training-control` Supabase Edge Function validates the signed-in Supabase user against `ULTRON_OWNER_USER_ID` before every action. It calls GitHub using a server-side `ULTRON_GITHUB_TOKEN`; no GitHub credential is present in browser code.
- The function supports status, start and stop. Stop cancels the active GitHub Actions workflow; Pause is intentionally absent because the training worker has no safe remote pause protocol.
- Start requires an explicit confirmation in the dashboard. It can launch a real neural training session, so do not press Start until the owner has reviewed the configured GitHub Actions secrets and explicitly intends to train.
- This branch is stacked on PR #50 and must not be merged before PR #50. No production Supabase Edge Function has been deployed and no production secret has been changed by this code change.
- Deployment gate: configure Supabase Edge Function secrets `ULTRON_OWNER_USER_ID` and `ULTRON_GITHUB_TOKEN`; the GitHub fine-grained token should be restricted to this repository with Actions read/write and Contents write (for repository dispatch). Deploy the function with JWT verification enabled. Verify unauthenticated and non-owner requests fail before testing any real Start action.
- The GitHub Actions runner also requires repository variable `SUPABASE_URL` and repository secrets `SUPABASE_SECRET_KEY` plus `SUPABASE_OWNER_ID`. These must be configured under the repository Actions settings. Never place these values in dashboard files or notebook source.
- The training workflow now names each dispatched run with its server-generated request ID to improve status visibility.
- RAM slider remains a browser preference only; it does not enforce a cloud runner memory limit.
- Next: inspect the full diff, run CI and security regression checks, then complete the deployment checklist only after code review. Do not start training during validation.


