# ULTRON — current project status (2026-11-20)

## Overall ULTRON completion estimate — 2026-11-21

**Estimated whole-project completion: 33%.** This is a milestone-based engineering estimate, not a line-count or feature-count metric. It includes the website, security, data pipeline, model, evaluation, compute/recovery, testing and release readiness. The estimate is deliberately conservative: conversational mathematics and the Stage 3 tutoring/Axiom Bank baseline are merged and independently tested, but physical-device verification, live security checks, a machine-checked proof kernel, deeper diagnosis, remaining dashboard integration and later reasoning stages remain open; the neural model has not been trained; production training readiness is not established. The increase to 33% reflects the merged conversational tutor, researched axiom catalog, Stage 4 proof replayer, proof-soundness fixes and strict AST validation. The neural model remains untrained and production training readiness is not established. Increase this figure only when substantial work is implemented and independently validated. Report this estimate in every progress update and revise it when evidence changes.

## Legacy pull-request reconciliation — 2026-11-20

The legacy PR backlog was reviewed against `main` at `346b36a940f5f662c07bc3b07e741c731be625a4`.

- **Closed as obsolete/superseded:** PR #4 (device-control/pairing contract; pairing and remote-device control are no longer part of the product), PR #25 (local CLI dummy worker; not the iPad-first website-controlled workflow and no verified RAM enforcement), PR #29 (stale README-only correction), PR #26 (older architecture note), PR #37 and PR #54 (their useful content has been selectively integrated into PR #99).
- The older PR #37's 42-question fixture and duplicate model-evaluation CLI were not copied. Current `main` has a newer frozen 18-example fixture and read-only scorer; PR #99 documents how to connect model inference to it without mixing scoring and training.
- No legacy branch was merged. No training, compute diagnostic, model-weight update, checkpoint mutation, Supabase deployment or production configuration change was performed.
- Future code changes must start from current `main`, port only still-valid functionality, add regression tests, update this README, and require fresh CI plus exact-diff review before merge.


## Combined reasoning and evaluation architecture — PR #99 merged

- PR #54's conversational reasoning, formal axioms/proofs, structured problem pipeline, verifier-first response contract, teaching, memory and staged delivery design is being retained in `docs/CONVERSATIONAL_REASONING_ARCHITECTURE.md`.
- PR #37's held-out evaluation goals are integrated into that architecture, but its older 42-question fixture and duplicate model-evaluation CLI are intentionally not copied.
- Current `main` already has a frozen 18-example / 18-topic held-out fixture (`evaluation/heldout_foundation_v1.json`), independent dataset validation, and a read-only explicit-prediction scorer (`ultron_evaluation.py`). The missing integration is a separately versioned model-inference adapter feeding predictions to that scorer; the scorer must remain read-only.
- The merged PR changed documentation only. No training, inference job, weight/checkpoint update, dataset mutation, production configuration change or Supabase deployment was performed.
- PR [#99](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/99) merged to `main` at `d087a9bc564556709ee7b457124997da236bef5e`. The combined reasoning/evaluation architecture is now part of `main`.


## Conversational mathematics shell — PR #100 merged

- Stage 1 adds a browser-local conversational layer over the existing deterministic math solver. It does not claim that the untrained transformer powers these answers.
- The conversation manager routes simple arithmetic, recognizes explicitly named foundation topics, asks a clarification when it cannot identify a supported question, and retains at most 20 user/assistant turns in memory.
- Each supported solution is passed through the existing independent verifier. Unverified answers are labelled; unsupported formats receive a format example rather than a fabricated solution.
- Conversation context is memory-only: it is not written to localStorage, Supabase, the Data Library, checkpoints or training datasets. Reset clears the session. No automatic chat ingestion or training is implemented.
- Browser UI uses DOM text nodes rather than injecting user content as HTML. The existing single-question solver and bounded benchmark remain available separately.
- A WebKit run exposed 320px horizontal overflow from Math-view status labels; the labels now wrap at narrow widths and dashboard grid children have min-width constraints. Chromium and WebKit browser smoke both pass on the final PR commit.
- Regression tests cover arithmetic routing, all 18 registered topics, supported/unsupported decimal operations, clarification, bounded history, reset, invalid/oversized input, independent verification and immutable history snapshots. The Test Suite workflow now runs the Node.js browser-module tests and syntax checks, rather than leaving the JavaScript test files outside CI.
- PR [#100](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/100) merged to `main` at `719247ec50f308227a85a8f102f7da8e74f0f377`. Test Suite, preflight, Training Prototype Validation, Chromium and WebKit checks all passed on the reviewed PR head (`808fe2ab56ee1c55c7b5aea60a6e0eb3272d4346`).
- This is Stage 1 only. It is not general natural-language mathematical parsing, formal proof checking, neural inference, or durable learner memory. Those require later independently tested stages.
- No model weights, datasets, checkpoints, Supabase configuration, production secrets or training state are modified.

## Stage 2 — structured reasoning kernel — PR #101 merged

- Added a versioned typed problem representation for all 18 supported foundation topics, including domain, operands, assumptions and the original source question.
- Built explicit operation plans from the existing deterministic solver output. Each explanatory step is marked as reproducibly matched, not as a formally proven derivation.
- Independently verify final answers through the existing topic-specific verifier; malformed or unsupported structures are rejected rather than guessed.
- Added deterministic report replay so tampered problem, plan, answer, explanation, knowledge or verification fields are detected; the typed parser registry is frozen.
- Integrated the typed problem summary into the browser conversation and added regression/browser coverage.
- PR [#101](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/101) merged to `main` at `ceaff2017ad42030e736e51a86fe40c676154c37`. Test Suite, preflight, Training Prototype Validation, Chromium and WebKit all passed on reviewed PR head `e04e49528e82ef53ef8723eb0d3f6d8ac01c0f53`.
- No changes to model weights, datasets, checkpoints, Supabase, training state or external services.

## Latest verified status — PR #96 merged and deployed

- PR [#96](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/96) merged to `main` at `397199389a1c829ff3107cff5560a2c27516fd9a`.
- The PR adds Playwright WebKit coverage beside Chromium and fixes the genuine 320px Settings overflow: the RAM panel heading/status pill and value row now wrap without forcing a 387px minimum width.
- Browser smoke checks passed in **Chromium and WebKit**, including all 11 navigation views, Guest Mode, optional owner sign-in dialog, local RAM preference persistence/disclosure, theme toggle, 44px touch targets, and no horizontal overflow at 320, 360, 390, 768, 1024 and 1366px. The RAM panel and slider receive explicit geometry assertions at every width.
- The complete post-merge **ULTRON Test Suite** passed (236 unit tests, static JavaScript checks, JSON/notebook validation, secret scan, Python compilation, model/data/checkpoint/training smoke checks).
- The complete post-merge **ULTRON preflight** passed, including Deno 2.9.8 type-check, 236 unit tests, model parameter-count verification, generated mathematics checks, checkpoint save/restore, training-loop smoke test and platform preflight.
- The **GitHub Pages build and deployment succeeded** for the exact merge commit. Dashboard: [https://shayaanfarsheed-cmd.github.io/ULTRONAI/](https://shayaanfarsheed-cmd.github.io/ULTRONAI/).
- The pre-merge **Training Prototype Validation** also passed: configuration, unit/recovery tests, and bounded data/checkpoint/optimizer smoke tests.
- The dashboard contains 11 views: Overview, How ULTRON learns, Data library, Ask ULTRON, Math Agent, Activity, Training control, Device access, Servers, Checkpoints and Settings. Guest browsing is public; private owner operations remain separately gated.
- The Settings RAM slider is a **browser-local preference**. It does not control hosted-runner RAM or GPU VRAM. Device access is browser-based; device pairing/local training agents are not used.
- Supabase `training-control` remains **ACTIVE, version 6**, with `verify_jwt=true`; its deployed source matches exactly with GitHub `main` (previously compared byte-for-byte).
- The preflight includes the pinned Deno 2.9.8 Deno type-check for `supabase/functions/training-control/index.ts`.
- Remote launch remains limited to the owner-confirmed GitHub Actions CPU diagnostic. Google Colab remains manual-only. **Actual model training has not started.**
- Remaining manual gates: open the deployed dashboard on a physical iPad/phone, use owner-only **Refresh status** from the signed-in owner's browser to verify GitHub API permissions, and complete live production security checks for invalid/expired JWTs, non-owner denial, public dispatch denial and secret non-disclosure.
- No diagnostic was launched, no model training was started, and no weights or persistent checkpoints were modified during this work.

## Immediate next steps

1. Perform the physical iPad and phone visual/accessibility smoke test; emulated WebKit is not a substitute for real-device verification.
2. Run owner-only **Refresh status** in the signed-in owner's browser and verify the expected GitHub API permissions without exposing the token.
3. Complete the production security matrix: invalid/expired JWT, non-owner, untrusted origin, public dispatch denial and secret non-disclosure.
4. Finish model/dataset/evaluation/checkpoint recovery and training-resource readiness audits.
5. Keep actual training disabled until all readiness gates pass and the owner separately authorizes a tiny overfit experiment.

## Latest verified status — PR #83 merged; responsive navigation improved

- PR [#81](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/81) merged to `main` at `6866ddb91d8380bea2050c685d8fca589bfd0496`.
- PR [#82](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/82) merged to `main` at `a2dbf433ad23d8d781f2c8f6a69fa802ab6c014d`; all three required checks passed.
- PR [#83](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/83) merged to `main` at `1b1f04825353996d56569c2e47b961ce8c5e627c`; all three required checks passed.
- Narrow phone layouts now use three navigation columns, with two columns on very narrow screens; the existing tablet/iPad and desktop layouts are preserved.
- The runtime regression test verifies a delayed owner-only status response cannot restore private details or links after sign-out.
- The production Supabase `training-control` Edge Function remains **ACTIVE, version 5**, with `verify_jwt=true`.
- The GitHub Pages deployment for PR #82 completed successfully. PR #83's Pages deployment is being verified; do not claim its live CSS is deployed until that workflow succeeds.
- No diagnostic was launched, no model training was started, and no weights or persistent checkpoints were changed.

## Immediate next steps

1. Finish the compact-screen header layout fix and validate the complete CI suite.
2. Verify the Pages deployment after PR #83.
3. Complete responsive, accessibility, browser-console, and owner-only live status checks.
4. Continue the security matrix: invalid/expired JWT, non-owner denial, public dispatch denial, and secret non-disclosure.
5. Keep real training disabled until the full readiness matrix passes and the owner separately authorizes a tiny overfit experiment.

## Latest verified status — PR #82 merged; runtime owner-status race test added

- PR [#81](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/81) merged to `main` at `6866ddb91d8380bea2050c685d8fca589bfd0496`.
- PR [#82](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/82) merged to `main` at `a2dbf433ad23d8d781f2c8f6a69fa802ab6c014d`; all three required checks passed.
- The dashboard now has a Node runtime regression test that delays an owner-only workflow status response, simulates sign-out, then verifies the late response cannot restore private workflow details or a private run link in Guest Mode.
- The production Supabase `training-control` Edge Function remains **ACTIVE, version 5**, with `verify_jwt=true`; its deployed source was previously fetched and matched GitHub `main`.
- GitHub Pages deployment for the PR #82 merge is being verified. The hosted dashboard URL could not be fetched by the external page reader during this check, so do not treat that as a live browser smoke-test pass.
- No diagnostic was launched, no model training was started, and no weights or persistent checkpoints were changed.

## Immediate next steps

1. Finish the narrow-screen dashboard navigation adjustment and run all required checks.
2. Verify the GitHub Pages deployment after the PR #82 merge.
3. Complete the responsive, accessibility, browser-console, and owner-only live status checks.
4. Continue the security matrix: invalid/expired JWT, non-owner denial, public dispatch denial, and secret non-disclosure.
5. Keep real training disabled until the full readiness matrix passes and the owner separately authorizes a tiny overfit experiment.

## Latest verified status — PR #81 merged; owner-status race regression strengthened

- PR [#81](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/81) merged to `main` at `6866ddb91d8380bea2050c685d8fca589bfd0496`; all three required checks passed on the final commit.
- PR #81 invalidates in-flight owner-only workflow status responses after sign-out, owner-mode changes, provider changes, or a newer refresh.
- This follow-up adds a runtime regression test that executes the dashboard training-control script with a delayed private status response, signs the owner out, then verifies the late response cannot restore private workflow details or links.
- The production Supabase `training-control` Edge Function remains **ACTIVE, version 5**, with `verify_jwt=true`; its deployed source was previously fetched and matched GitHub `main`.
- GitHub Actions remote control remains diagnostic-only. No diagnostic was launched, no model training was started, and no weights or persistent checkpoints were changed.

## Immediate next steps

1. Complete the runtime race regression and full CI checks for the current PR.
2. Continue the responsive, accessibility, browser-console, and live dashboard checks.
3. Verify owner-only **Refresh status** from the signed-in owner's browser; configuration presence alone does not prove GitHub API permission.
4. Continue the security matrix: invalid/expired JWT, non-owner denial, public dispatch denial, and secret non-disclosure.
5. Keep real training disabled until the full readiness matrix passes and the owner separately authorizes a tiny overfit experiment.

## Latest verified status — PR #80 merged and production control function updated

- PR [#80](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/80) merged to `main` at `28d192221df13ff718dd273a58974d33f09c317e`; all three required checks passed: preflight, training-prototype validation, and the full test suite.
- The production Supabase `training-control` Edge Function is **ACTIVE, version 5**, with `verify_jwt=true`.
- The deployed function source was fetched after deployment and matched `supabase/functions/training-control/index.ts` on GitHub `main` exactly.
- The launch adapter now calls GitHub's `workflow_dispatch` endpoint for `cpu-diagnostic.yml`. The obsolete `repository_dispatch` route is removed. This uses the intended Actions write permission without requiring Contents write.
- Owner-only **Check connection** passed in the owner's browser: owner verification is active and the GitHub token is present. This confirms configuration presence, not successful GitHub API authorization.
- The next live integration check is owner-only **Refresh status**. It must successfully read the CPU diagnostic workflow runs before any diagnostic dispatch is considered.
- No diagnostic was launched and no model training was started. No weights or persistent checkpoints were changed.

## Immediate next steps

1. Verify owner-only **Refresh status** succeeds against GitHub Actions using the configured fine-grained token.
2. If it succeeds, review the returned workflow status and run link; only then perform a separately confirmed CPU diagnostic dispatch/cancellation test.
3. Complete the dashboard's responsive, accessibility, stale-response, and browser-console checks. The current patch adds a guard so a delayed private status response cannot repaint the page after sign-out or an owner-mode transition.
4. Continue the security matrix: invalid/expired JWT, non-owner denial, public dispatch denial, and secret non-disclosure.
5. Keep real training disabled until the complete readiness matrix passes and the owner separately authorizes a tiny overfit experiment.

## Authoritative model baseline correction

- The current baseline tokenizer has **80 characters** after the semicolon and exponent-caret compatibility fixes.
- The current baseline model has **4,039,504 trainable parameters**, with a 192-character context (one character per token).
- Older sections below that cite 78 characters / 4,038,478 parameters describe the pre-expansion architecture and must not be used as the current configuration.
- Checkpoints from earlier vocabulary sizes are incompatible and must be rejected by checkpoint validation.
- This documentation correction does not alter model code, weights, datasets, checkpoints, or training state. No real training has started.


**Current phase:** Phase 2 compute diagnostics completed; production-safe remote-control function deployed for diagnostic-only operations. No real training is authorized or started.

## Dashboard access and control boundaries

- The dashboard is publicly browsable without creating an account or signing in.
- Optional owner sign-in is reserved for privileged diagnostic controls; it is not required for ordinary dashboard viewing.
- Public self-registration, device pairing, remote device commands, and account-specific training history are not part of the current product.
- The production control endpoint must independently verify the owner identity; browser-side checks are only a user-interface convenience.
- The only remotely dispatchable workflow is the CPU compute diagnostic. It does not train the model or touch checkpoints.
- This documents the current boundary; it does not change authentication, production secrets, database policies, or Edge Function behavior.

## Dashboard diagnostic status refresh fix

- Fixed the launch flow so the busy state is cleared before requesting the updated workflow status.
- Previously, the immediate refresh returned early while the launch request was still marked busy; the UI could remain stale until the next 60-second poll.
- Added a regression test to keep the post-launch refresh after the busy-state cleanup.
- This is a dashboard status-display fix only. It does not change workflow dispatch, authentication, model training, weights, checkpoints, or production secrets.

## Dashboard wording correction — diagnostic stop behavior

- Corrected the Stop confirmation: it now accurately says it cancels the CPU diagnostic and does not create, modify, or delete checkpoints.
- Removed the misleading suggestion that a training checkpoint may be retained; the remotely controlled workflow is diagnostic-only and never runs training.
- Added a regression test to prevent this mismatch from returning.
- This is a UI copy and test change only. No production function, secrets, database, checkpoints, model weights, or training state changed.

## Latest verified milestone — PR #78 deployed (2026-11-20)

- PR [#78](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/78) merged to `main` at `f75f5d276b3a108de57d5ebb5226d86975163af7`; all three required PR checks passed.
- Supabase project `ultron-memory` (`euhmejpaswmdpsutbtse`) reports `ACTIVE_HEALTHY`. The `training-control` Edge Function is `ACTIVE`, version **3**, with platform JWT verification enabled (`verify_jwt = true`).
- The deployed version 3 source was fetched and matched against `supabase/functions/training-control/index.ts` on `main`.
- The function keeps the GitHub Pages origin restriction, validates the signed-in Supabase user against server-side `ULTRON_OWNER_USER_ID`, and dispatches only `ultron-cpu-diagnostic.yml`. It never dispatches the training workflow. Colab remains manual-only.
- Version 3 separates missing `SUPABASE_URL` and missing `ULTRON_OWNER_USER_ID` diagnostics. Both paths fail closed and never disclose a secret or owner ID.
- Dashboard `dashboard/training-control.js` contains the owner-only **Check connection** action. It reports only whether owner verification and the GitHub token are configured; it does not reveal either secret.
- **Still unverified:** the owner-only health request has not been retested after the version 3 deployment from the owner's signed-in browser session. Secret values are not readable through connected tools, so their presence cannot be independently verified here. Do not start a diagnostic until health and GitHub Status both succeed.
- No training was started; no model weights or persistent checkpoints were modified.

## Phase 2 compute diagnostic results

- GitHub Actions CPU diagnostic passed on run [44669274325](https://github.com/shayaanfarsheed-cmd/ULTRONAI/actions/runs/44669274325): 4 logical CPUs, approximately 15.6 GiB available RAM, approximately 92.3 GB free disk, Python 3.11.18, PyTorch 2.15.0+cpu, no CUDA.
- Google Colab manual diagnostic passed on 2026-11-20: 2 logical CPUs, approximately 12.67 GiB system RAM (11.08 GiB available), approximately 112.5 GiB free root disk, Python 3.13.16, PyTorch 2.14.1+cu130, NVIDIA Tesla T4 with 15 GiB GPU memory and CUDA 13.0.
- Colab diagnostic explicitly reported `training_started=false`, `model_weights_modified=false`, and `persistent_checkpoints_touched=false`.
- Colab Free is manual-only; GPU access is temporary and not guaranteed. GitHub Actions is the CPU fallback. Neither provider is a guaranteed always-on GPU service.

## Immediate next steps

1. In Supabase Dashboard → Edge Functions → Secrets, verify `ULTRON_OWNER_USER_ID` exists and matches the owner's Supabase Auth user UUID. Never paste its value into chat or the website.
2. Open the GitHub Pages dashboard, sign in with the owner account, and click **Check connection**. Confirm `owner_verification_configured: true`; the same result reports only whether `ULTRON_GITHUB_TOKEN` is present.
3. If the GitHub token is reported present, click **Refresh status** and verify the GitHub API/repository permissions. If either check fails, inspect the safe error and Edge Function logs; do not bypass owner checks.
4. Only after both checks pass, separately decide whether to run the CPU-only diagnostic. It is not model training and must not touch weights or checkpoints.
5. Keep real training disabled until the full authorization/readiness matrix passes and the owner separately authorizes a tiny overfit training test.

---


## Phase 1 result
- PR #68 merged to `main` at `f7dbd1b9e692d1fa12870372187a37533046b2e9`.
- The live Candidate 5 recovery workflow was reported by the owner as passed.
- Dataset workflow run [44655730066](https://github.com/shayaanfarsheed-cmd/ULTRONAI/actions/runs/44655730066) passed: 110,000 examples (100,000 train / 5,000 validation / 5,000 test), 18 topics, fixed-seed reproducibility, quality audit, and artifact upload.
- The dataset artifact is retained for 30 days. Dataset audit success is not proof of model capability.

## Free compute-provider review (2026-11-20)

- **GitHub Actions public-repository CPU:** this repository is public. GitHub documents standard `ubuntu-latest` runners as 4 logical CPUs, 16 GB RAM and 14 GB SSD, with standard hosted runners free and unlimited for public repositories. Each job is limited to 6 hours. These are published baselines; the new diagnostic will measure the actual allocated runner and filesystem. Sources: [runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) and [Actions limits](https://docs.github.com/en/actions/reference/limits).
- **Google Colab Free:** free GPU access may be offered, but hardware and usage limits are dynamic, not guaranteed or published as fixed quotas; free notebooks can run for at most 12 hours depending on availability and usage patterns. Google explicitly disallows remote control / bypassing the notebook UI on managed free runtimes. Therefore Colab stays manual notebook-only and is not a dashboard-controlled worker. Source: [Colab FAQ and resource limits](https://research.google.com/colaboratory/faq.html).
- **Current provider decision:** GitHub Actions is the repeatable CPU diagnostic/fallback provider; Colab is a possible manually operated GPU runtime when Google offers one. Neither is a guaranteed always-on GPU service. No paid provider or payment method is considered.

## Phase 2 scope
- Add a read-only GitHub Actions CPU diagnostic that measures visible CPU, memory/cgroup limits, root disk, Python, PyTorch and installed package versions.
- Add a separate manual Google Colab diagnostic notebook to report the actual assigned CPU/RAM/disk/PyTorch/GPU; it performs no training and uses no credentials.
- The diagnostic does not import or call the training loop, does not modify model weights, and does not access Supabase or persistent checkpoints.
- Route the dashboard's owner-only Start/Status/Stop control to the diagnostic workflow rather than the real training workflow.
- Keep the actual `cpu-training.yml` workflow separate and unchanged in behavior.
- Upgrade GitHub Actions used by the repository to Node.js 24-compatible major versions.
- Add regression tests for diagnostic output and ensure the workflow cannot start training or access secrets.

## Critical deployment boundary (superseded by deployment milestone above)
The diagnostic-only `training-control` Edge Function is now deployed with JWT verification enabled. Its source dispatches only `cpu-diagnostic.yml`. However, end-to-end owner/non-owner authorization and runtime-secret configuration still require verification. Do not use production dashboard Start until those checks pass. The deployed function does not authorize or invoke real model training.

## Phase 2 validation sequence
1. Review this PR and pass CI.
2. Merge only after explicit owner approval.
3. Manually run **ULTRON Safe CPU Compute Diagnostic** from GitHub Actions; inspect its JSON report and artifact.
4. Open `compute_provider_diagnostic.ipynb` in Google Colab and run its cells manually; record whether a free GPU is offered and its actual resources. Do not connect Colab Free to remote dashboard controls.
5. Separately approve and deploy the diagnostic-only `training-control` Edge Function; verify missing/invalid/expired JWT, non-owner denial, owner status/start/stop, and public dashboard denial.
6. Test cancellation of a diagnostic run and verify no training or checkpoint writes occur.
7. Document actual runner resources and free-tier limits. GitHub-hosted runner resources are provider-managed; the dashboard RAM preference is not a hard cap.
8. Do not begin the 100-example overfit experiment until the user separately approves the tiny diagnostic training test and all safety gates are satisfied.

## Current safety status
- No model training started.
- No model weights or production checkpoints changed.
- No Supabase schema, RLS, Storage bucket, persistent checkpoint, or secret changed.
- No paid compute, payment method, quota bypass, pretrained weights, external AI API, or externally generated training data.

---

## PR #68 review correction — unsorted median inputs (2026-11-20)

- Review found the median-and-range generator sorted values before presenting the question, which made the median task easier than intended and did not require sorting.
- The generator now presents the original unsorted values while independently calculating the median/range from a sorted copy. The solution target explicitly shows the sorted sequence.
- Added regression coverage requiring unsorted examples and independent verification of all generated solution steps.
- This is a data-quality correction only. No model weights, training configuration, remote storage, or production checkpoints were changed. PR #68 remains unmerged; rerun CI on the updated head before considering merge.

## Exponent tokenizer compatibility repair — PR #68 (2026-11-20)

- The next CI run exposed that generated exponent examples contain the caret character `^`, which was also missing from the character tokenizer.
- Added `^` alongside the previously added semicolon; vocabulary size is now 80.
- Updated expected parameter counts: baseline 4,039,504; Candidate 5 25,400,400.
- This is another model-shape change. Checkpoints made with earlier vocabularies are shape-incompatible and must be rejected, not silently loaded.
- Re-run all CI checks on the latest PR head. No training has started.

## Tokenizer vocabulary compatibility repair — PR #68 (2026-11-20)

- CI exposed that the canonical median-and-range answer uses a semicolon, but the character tokenizer alphabet did not include it. This caused generated examples to fail tokenization before training.
- Added the semicolon to the project character vocabulary and updated the configured vocabulary size from 78 to 79.
- Updated the baseline model parameter-count expectation to 4,038,991 and Candidate 5 to 25,399,375 because the untied input embedding and output projection each grow with the vocabulary (including the output bias).
- This is an architecture compatibility change. Existing checkpoints created with the old vocabulary shape are not interchangeable with the updated model and must not be restored as if compatible.
- CI must be rerun on the latest PR head. No training has started; do not merge until all required checks pass and the diff is reviewed.

## PR #68 CI failure repair — expanded solver compatibility (2026-11-20)

- Latest CI exposed Python agent regexes that matched a literal backslash instead of decimal digits for simple-interest, metric-conversion, and Pythagorean inputs. Corrected those patterns.
- Aligned the Python median-and-range answer format with the canonical frozen fixture (`median=...; range=...`).
- Added the four newly introduced topics to the browser math agent: median/range, simple interest, metric conversion, and Pythagorean hypotenuse. Added independent browser-side answer checks and deterministic generators for those topics.
- Updated browser held-out tests to derive sample counts from the fixture rather than hard-code the former 14-example size.
- CI rerun is required on the latest head. No merge, live Supabase recovery, dataset artifact build, or model training has been performed.

---

## PR #68 review correction — held-out fixture and evaluator regression (2026-11-19)

- Code review found that the four newly added frozen evaluation examples increased the fixture from 14 to 18, while evaluator tests still hard-coded the old total (14) and incorrect-score total (13). Updated these assertions to derive expected counts from the fixture length.
- The new median-and-range held-out example used a comma-separated answer while the independent verifier and generator use the canonical `median=...; range=...` format. Corrected the fixture answer and final solution step to the canonical format.
- Added a regression test that independently verifies every frozen held-out answer and solution-step sequence, not just the generated training examples.
- These are pre-merge code-review corrections. Required CI is rerunning on the latest PR head; no merge, live Supabase test, dataset build, or training run has been performed by this correction.

---

# ULTRON recovery and mathematical data-quality milestone — implementation in review (2026-11-19)

- Active branch: `feat/ultron-recovery-and-math-data-quality`. PR #68 contains one combined pull request covering recovery fault testing and a reproducible mathematics dataset pipeline.
- PR #67 was merged at `19ece113483a01c963c28ef84d398890dfa38af7`; its three required CI workflows passed. The live Candidate 5 Supabase interrupted-resume workflow is still a separate post-merge manual test and must be run before claiming live recovery is validated.
- Recovery implementation now fault-injects a corrupted tensor component and a missing tensor component inside the unique temporary Supabase checkpoint prefix. It requires both faults to be rejected, restores the original temporary component, verifies the valid checkpoint again, and then proceeds to the exact uninterrupted-vs-resumed next-update comparison. Cleanup remains scoped to the unique temporary prefix and is verified in a finally block.
- The live recovery entrypoint now requires explicit passing flags for corruption rejection, missing-component rejection, repaired-checkpoint acceptance, exact model/optimizer/scheduler/data-stream/curriculum/scaler continuation, and optimizer parameter binding. CI fake-storage coverage is not live Supabase evidence.
- The mathematical generator now covers 18 topics and rotates each topic through all three difficulty levels rather than coupling difficulty to topic index. Four new topics were added: median and range, simple interest, unit conversion, and the Pythagorean theorem. Each has independent answer and solution-step verification in `ultron_verify.py`. Generator inputs now reject invalid difficulty, seed, count, topic duplicates and invalid attempt limits rather than silently accepting them.
- Added `ultron_dataset_quality.py` for independent answer verification, normalized exact duplicate detection, deterministic split-assignment checks, cross-split exact and high-similarity near-duplicate rejection, structural-template overlap reporting, topic/difficulty/split counts, and a deterministic dataset digest. Structural-template overlap is reported separately because distinct numeric questions using the same mathematical method are not automatically leakage; the report must be reviewed.
- Added `scripts/build_math_dataset.py` to build 100,000 training + 5,000 validation + 5,000 test examples (110,000 total), independently verify every example, audit quality, check all topics and all three difficulty levels per topic in training plus split coverage, and verify fixed-seed reproducibility on a bounded independent slice. The builder reserves and includes all examples from the canonical frozen held-out evaluation fixture in the test split, then audits the combined data for leakage. It writes JSONL split files and a manifest with SHA-256 hashes. This is an initial foundation corpus, not proof that the model has enough data to achieve any target competence.
- Added manual-only workflow `.github/workflows/math-dataset-build.yml`. After this PR is merged, manually run **ULTRON Build and Audit Mathematics Dataset** from GitHub Actions. It builds the 110,000-example dataset and uploads the versioned files and audit manifest as a 30-day artifact. This is a dataset-build job, not model training.
- Current status: PR #68 is open; required CI checks are running on the current head. Do not mark the recovery or dataset gates as passed until CI and the post-merge manual workflows complete successfully.
- Next: finish regression tests and code review; run required PR checks; fix failures; merge only after checks pass and explicit owner approval. After merge, run the live Candidate 5 Supabase recovery workflow and the dataset-build workflow, inspect their structured reports and artifacts, then report any remaining quality limitations.
- Safety: no real training has started; no production model weights/configuration were changed; no Supabase schema, RLS, bucket, Edge Function, secret, or persistent checkpoint was modified. No external AI API, pretrained weights, existing model, or externally generated training data is used.

---

## Candidate 5 live Supabase checkpoint test — implementation in review (2026-11-19)

- Branch: `test/candidate5-live-supabase-checkpoint`.
- Added `scripts/verify_candidate5_supabase_checkpoint.py`, which instantiates the exact Candidate 5 architecture (512 width, 8 layers, 16 heads, context 192; expected 25,398,350 parameters), performs one deterministic optimizer update so AdamW moments are populated, writes a sharded checkpoint, uploads every component to the existing private `checkpoints` bucket, verifies remote component hashes, downloads into a fresh local directory, and checks exact model, AdamW, and scheduler restoration.
- Added manual-only workflow `.github/workflows/candidate5-live-storage.yml`. It runs only on explicit `workflow_dispatch`, uses existing GitHub Actions secrets, and never exposes credentials to pull-request code.
- The test uses a unique `SUPABASE_OWNER_ID/candidate5-live-<run-id>` prefix and removes only objects under that exact prefix in a `finally` cleanup. It does not overwrite persistent checkpoints or change Supabase configuration.
- The 45,000,000-byte per-object limit is checked locally before upload. **Total remaining Supabase bucket quota is not available through the current Storage API integration and is reported as UNKNOWN**; the upload itself is the provider-side capacity test. Do not infer total capacity from per-file limits.
- This is a storage/reload test, not a training run or proof of mathematical capability. Candidate 5 remains unpromoted; production config is unchanged and real training remains disabled.
- Next: complete required CI checks and review PR. After merge, manually dispatch **ULTRON Candidate 5 Live Supabase Checkpoint** on `main`; inspect upload, hash verification, fresh restore, and cleanup logs. Only after this passes should we run a separate full Candidate 5 interrupted-resume validation against the live provider.

---

## Candidate 5 checkpoint and recovery validation — in progress (2026-11-19)

- Started branch `test/candidate5-checkpoint-recovery` after the Supabase storage smoke-test repair.
- Extended the isolated remote recovery harness to accept an explicit architecture while preserving the existing small fast test default.
- Added a Candidate 5 regression using the target architecture: width 512, 8 layers, 16 heads, feed-forward multiplier 4, context 192, expected 25,398,350 parameters.
- The regression exercises a two-step update, sharded local checkpoint creation, remote fake-storage upload/manifest verification/download, fresh model+AdamW+scheduler restore, one resumed update, exact comparison against uninterrupted execution, and temporary-object cleanup.
- This CI regression is a deterministic fake-storage test; it is not evidence that a 300+ MB Candidate 5 checkpoint fits the live Supabase bucket quota or that the real provider can upload/download all shards.
- No production model configuration was changed. No real training was started.
- Next: run all required CI checks. If they pass, add/execute a separately isolated live Supabase Candidate 5 round-trip with quota preflight and run-specific cleanup before considering production promotion.

---

## Latest update — 2026-11-19 (Supabase smoke-test URL fallback)

- The live checkpoint smoke test failed because the GitHub Actions runner received an empty `SUPABASE_URL`, even though `config.json` already declares the project's public URL.
- The manual workflow now uses the repository variable `vars.SUPABASE_URL` when set, otherwise it falls back to the project URL already recorded in `config.json`: `https://euhmejpaswmdpsutbtse.supabase.co`. This URL is not a secret.
- `SUPABASE_SECRET_KEY` and `SUPABASE_OWNER_ID` remain required repository secrets. The verifier must continue to fail closed if either is missing. Secret values must never be pasted into chat, committed, or exposed to browser code.
- This change only fixes workflow configuration; it does not prove the storage round trip. Run the manual workflow after this PR is merged and inspect upload, hash verification, download, restore, and cleanup.
- Repository audit also found documentation drift: older README sections describe superseded access-control and validation states. Reconcile the README after the storage fix is verified. Dataset leakage prevention, a broad frozen evaluation benchmark, and formal proof-engine capability must not be described as complete without dedicated tests/evidence.
- No real training has started. Keep Candidate 5 and production training blocked until live storage, candidate checkpoint restore, and interrupted-resume gates pass.

---

## Latest update — 2026-11-19 (checkpoint storage smoke test failure diagnosis)

- Manual workflow run `44537738778` failed in its verification step before making any Supabase request. The direct cause was `ModuleNotFoundError: No module named 'ultron_checkpoint'` because executing `scripts/verify_supabase_checkpoint_storage.py` places the `scripts/` directory, not the repository root, on Python's import path.
- Branch `fix/checkpoint-smoke-import-path` adds the repository root to `sys.path` before importing ULTRON modules. This makes direct script execution reliable in GitHub Actions and local diagnostics.
- The same run's log showed `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `SUPABASE_OWNER_ID` were empty in the runner environment. Once the import issue is fixed, the workflow will intentionally stop with a missing-configuration error until the repository variable/ secrets are configured. Do not paste secret values into chat.
- Node.js 20 messages for `actions/checkout@v4` and `actions/setup-python@v5` are deprecation warnings, not the cause of this failure.
- No Supabase upload, download, deletion, or real training occurred in failed run `44537738778`. The storage round-trip remains unvalidated. Next: review/test the import-path fix, merge only after checks pass and owner approval, configure any missing GitHub Actions values, then rerun the smoke test and verify cleanup.

---

## Latest validation — 2026-11-19 (PR #61 checkpoint sharding)

- Latest validated code head before this README-only update: `e32d6fa93960112de3f4c09604378e87ae251c19`.
- All three required GitHub Actions workflows passed on that head: ULTRON Test Suite (run `44533586012`, 184 tests), ULTRON preflight tests (run `44533585888`), and ULTRON Training Prototype Validation (run `44533586061`). The test suite and both validation workflows reported successful bounded training/checkpoint smoke tests.
- PR #61 is open and mergeable; it has not been merged. The README-only status update will trigger fresh PR checks.
- The live Supabase Storage smoke workflow is manual-only and has not been run. After PR #61 is merged, run **ULTRON Checkpoint Storage Smoke Test** from Actions and verify its round-trip and cleanup success before any real training.

---

## Latest update — 2026-11-19 (live checkpoint storage smoke workflow added)

- PR #61 now includes a manual-only GitHub Actions workflow, `.github/workflows/checkpoint-storage-smoke.yml`, and `scripts/verify_supabase_checkpoint_storage.py`. It uses the existing `SUPABASE_URL` repository variable and `SUPABASE_SECRET_KEY` / `SUPABASE_OWNER_ID` secrets, writes one tiny synthetic checkpoint beneath a unique run-specific prefix in the existing private `checkpoints` bucket, verifies remote hashes, downloads it, restores model and AdamW moments, and deletes only objects beneath that exact temporary prefix in a `finally` cleanup.
- This workflow does not start training or alter bucket settings, schema, RLS, secrets, or persistent model checkpoints. It is `workflow_dispatch` only and becomes available after its workflow file is merged to `main`.
- Run it from GitHub Actions as **ULTRON Checkpoint Storage Smoke Test** after PR #61 is merged; confirm the final log says both the round-trip and cleanup passed. If the required repository secrets/variable are absent, the workflow fails closed before upload.
- PR #61 CI is still pending on the latest head. No production model change and no real training have occurred.

---

## Latest update — 2026-11-19 (Candidate 5 checkpoint sharding implementation in review)

- Branch `feat/checkpoint-sharding-candidate5` adds model and optimizer safetensors sharding, with a conservative per-shard byte budget below the configured 45,000,000-byte Storage cap. The manifest records every shard and its size/hash; restore recombines tensors and keeps compatibility with legacy single-file checkpoints.
- Supabase and Hugging Face checkpoint transfer now enumerate manifest-listed components rather than assuming exactly one model and optimizer file. Import validates the manifest and component paths before accepting a checkpoint.
- Added regression coverage that forces both model and optimizer into multiple small shards, restores model weights and scheduler state, and checks all components stay below the configured cap. Remote-storage corruption tests now target an actual model shard.
- CI and review are pending; this branch is not merged and Candidate 5 is not yet the production model.
- Live Supabase bucket inspection confirmed the existing `checkpoints` bucket is private with a 45,000,000-byte per-file limit. The connected Supabase integration in this session exposes SQL inspection but not Storage object upload/download/delete actions, so no live round-trip has been claimed or performed. The bucket quota and total-retention capacity remain unverified.
- No real training has started. Next gates: pass CI; verify the full Candidate 5 checkpoint size and sharding on a representative run; validate live Storage upload/download/delete using an authorized runtime with the configured secret; confirm quota/retention; then test interrupted resume on Candidate 5 before considering a production config change.

---

## Latest update — 2026-11-19 (Candidate 5 benchmark; PR #60 merged)

- PR #60 merged to `main` at commit `8268bd3ca48495655545b56ee76493022b748924`. All four required workflows passed, including all seven isolated model-capacity matrix jobs.
- The selected target candidate remains Candidate 5: width 512, 8 layers, 16 heads, context 192, approximately 25,398,350 parameters. Its isolated short CPU benchmark measured 0.674 steps/second and approximately 1,480 MB peak process RSS, with finite loss. This is a bounded diagnostic result, not a long-run training guarantee.
- Estimated checkpoint payload is approximately 304.8 MB before metadata. Model weights and Adam state exceed the current 45,000,000-byte single-component checkpoint limit. Candidate 5 is therefore a target architecture for the next engineering stage, **not yet the production model configuration**.
- Next required work: implement bounded checkpoint sharding, validate storage/quota and retention against the $0 infrastructure constraint, then test full Candidate 5 save/restore and interrupted-training resume. Only after those gates pass should production model configuration be changed.
- No production training was started. PR #60 only added diagnostic benchmark tooling and README documentation; it did not alter the production architecture or write to Supabase/Hugging Face.

---

## Model capacity benchmark merged — 2026-11-19 (PR #60)

- The pre-expansion 4,038,478-parameter architecture was a baseline, not an immutable limit. A bounded candidate sweep now measures widths/depths from approximately 4.83M through 56.97M parameters using ULTRON-generated, independently verified maths examples, the same 192-token context, batch size and 2-thread GitHub Actions CPU profile.
- Each candidate runs in its own isolated GitHub-hosted job so peak RSS is measured independently. The sweep reports measured step throughput, loss finiteness, peak process RSS, and estimated FP32 model/Adam checkpoint payload.
- Important constraint discovered during review: the current checkpoint format writes a single `optimizer.safetensors` component, and both local and remote checkpoint stores enforce a 45,000,000-byte per-component limit. Adam's two FP32 moment tensors alone need approximately 8 bytes per parameter, so larger candidates cannot be adopted safely until checkpoint sharding is implemented and tested.
- The sweep is diagnostic only: it does not change the configured production architecture, write checkpoints, call Supabase/Hugging Face, or start training. No new model size is selected until both CPU capacity and checkpoint save/restore limits are validated.
- Next: review sweep artifacts, implement bounded checkpoint sharding if needed, test full save/restore and interrupted resume at the selected larger architecture, then update the production model config only after those checks pass.

---

## Latest update — 2026-11-19 (realistic benchmark and interrupted-resume validation; PR in progress)

- Added `scripts/benchmark_math_data.py`, a bounded diagnostic that uses ULTRON's own generated and independently verified examples from the first configured curriculum stage.
- The benchmark instantiates the configured 4,038,478-parameter model, uses the GitHub Actions CPU runtime profile (2 PyTorch threads, configured CPU batch size), configured context limit (192), AdamW defaults and cosine learning-rate scheduler. It reports actual batch tensor shapes, finite losses, steps/second, median/mean step time, and process peak RSS.
- Final bounded GitHub Actions run (1,024 verified examples, 2 warmup steps, 10 measured steps): **5.09 steps/second**, 0.197 s mean step, 0.196 s median step, 709.6 MB peak process RSS, and finite mean loss 3.039. Timing includes batch selection/collation plus forward/backward, optimizer, and scheduler. Batch size was 8; all 12 observed sequence lengths were below the configured 192-token context cap (range 123–151). Data generation took 0.055 s and dataset encoding took 0.013 s. This is a bounded result from one GitHub-hosted runner, not a long-run throughput guarantee.
- The benchmark is isolated: it does not call Supabase, Hugging Face, the production training-session entry point, or checkpoint storage. Model updates exist only in benchmark process memory.
- Added a separate GitHub Actions workflow for pull requests touching the model/data/training pipeline and manual bounded runs. It has no production secrets and cannot start a production training session.
- Added a session regression test that injects a KeyboardInterrupt after one optimizer update, verifies the checkpoint is committed, starts a fresh session/runtime, and verifies training resumes from the saved step and reaches the next step.
- Added a full configured-architecture checkpoint test: the 4,038,478-parameter model trains one generated-data batch, saves model/AdamW/scheduler/RNG/data-stream state, restores into fresh objects, and checks exact state equality. This is local temporary storage only.
- Existing checkpoint tests also cover atomic local save, integrity verification, fallback to an earlier valid checkpoint, optimizer/scheduler/RNG restoration, remote-storage round-trip with fake storage, interrupted upload/download cleanup, and exact next-update equivalence in the isolated recovery test. Fake-storage checks are not proof of live Supabase behavior.
- The 10-step/1,024-example generated-data benchmark passed on GitHub Actions CPU. The full configured-model checkpoint test and KeyboardInterrupt/fresh-session resume regression passed in the unit-test suite. All four required workflows passed on the latest tested PR head.
- No live Supabase Storage writes, production run, or real training session were started.
- Next: review and merge this PR only after explicit owner approval. Live Supabase checkpoint upload/download/recovery is still not validated by fake storage or local tests; it requires a separately approved isolated test because it writes temporary objects to the private production bucket. Keep production training disabled.

---

## Latest update — 2026-11-19 (CPU benchmark settings alignment; PR in progress)

- The isolated GitHub Actions CPU benchmark compared 1 versus 2 PyTorch threads and AdamW foreach on/off.
- The 20-step synthetic benchmark's best observed setting was 2 threads with AdamW foreach disabled (22.70 steps/second; 43.58 ms median step). The other tested settings were slower on that runner.
- The synthetic benchmark is diagnostic only: it uses random token batches of shape 2 × 64, not ULTRON's generated math dataset or production sequence length. These results do not establish end-to-end training throughput.
- The GitHub Actions runtime profile already selects 2 CPU threads. This PR changes the CPU AdamW default to foreach OFF, matching the measured winner. Other devices keep their previous OFF-by-default behavior; `training.adamw_foreach` can explicitly override the default.
- No model architecture, training objective, data generation, optimizer hyperparameters, checkpoint format, or provider workflow trigger is changed.
- No production training, Supabase operation, or checkpoint write is started.
- Next: add a bounded benchmark using ULTRON's verified generated training examples and configured sequence length, then separately test checkpoint round-trip/recovery before any training authorization.

---

## Latest update — 2026-11-19 (Data Library 500-file upload message fix in progress)

- The dashboard HTML incorrectly described the 500-file internal batch size as a 500-file total upload limit, and could remain stale in browsers using a cached `app.js` asset.
- The UI now states the actual limits: up to 50,000 selected files, 20 MiB per file, and 5,000 MiB (5 GiB) total. Upload requests are explicitly grouped into sequential batches of at most 500 files, with overall and per-batch progress.
- The `app.js` script URL receives a version query string so GitHub Pages clients fetch the corrected upload logic instead of reusing an older cached script.
- Owner verification and private Storage access remain unchanged. Uploads remain storage-only and do not execute files or start training.
- Regression assertions cover the displayed limits and 500-file batching. CI and deployed GitHub Pages behavior must be checked before calling this fixed for everyone.
- Next: run the dashboard tests and required workflows, then merge only after review and explicit approval.

---

## GitHub Actions CPU performance tuning — 2026-11-19 (PR in progress)

- CPU training remains on GitHub-hosted Ubuntu runners; no paid runner or GPU is enabled.
- The workflow reports visible logical CPU count and PyTorch thread settings so tuning is based on actual runner hardware.
- CPU training configures PyTorch intra-op threads from the runtime profile and limits inter-op parallelism to one thread to reduce oversubscription.
- AdamW uses PyTorch's foreach implementation on CPU by default, with a training.adamw_foreach configuration override. This is a candidate optimization, not a claimed speedup; compare steps/second and peak memory on the same runner before keeping it.
- Pip installation is ordered so dependencies are installed after the pip upgrade, and the CPU-only PyTorch wheel index remains explicit.
- No model architecture, tokenizer, dataset, learning-rate schedule, checkpoint format, or training objective is changed.
- Validation must include the complete test suite, training smoke test, checkpoint save/restore, and a bounded non-production CPU throughput benchmark. No real training run is permitted during this optimization.
- Next: measure baseline versus tuned CPU steps/second and memory on GitHub Actions; retain only changes that improve throughput without harming numerical stability or recovery.

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

- From-scratch decoder-only Transformer with **4,039,504 trainable parameters**, character-level tokenization, an **80-character vocabulary**, 5 layers, embedding size 256, 8 attention heads, and context length 192 characters (one character per token).
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



## CPU benchmark workflow — 2026-11-19

- Added a separate manually triggered `ULTRON CPU Benchmark` workflow. It never invokes the production training entry point and needs no Supabase, Hugging Face, or owner secrets.
- It compares PyTorch CPU thread counts (1/2) and AdamW foreach (off/on) using a bounded synthetic batch, reporting steps/second and peak RSS.
- Results are diagnostic only: synthetic throughput is not a claim about full training speed. Runs are limited to 1–20 measured steps per configuration.
- Initial dispatch exposed a Python import-path bug because direct script execution added `scripts/` but not the repository root to `sys.path`. The follow-up fix explicitly adds the repository root before importing ULTRON modules; rerun the benchmark after its checks pass.


## Checkpoint storage smoke-test fix — 2026-11-19

- The first `ULTRON Checkpoint Storage Smoke Test` run failed before any Supabase request: direct execution of `scripts/verify_supabase_checkpoint_storage.py` could not import the root-level `ultron_checkpoint` module.
- The fix explicitly adds the repository root to `sys.path` before importing project modules.
- The same run showed empty workflow inputs for `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `SUPABASE_OWNER_ID`. Configure repository variable `SUPABASE_URL` and repository secrets `SUPABASE_SECRET_KEY` / `SUPABASE_OWNER_ID` in GitHub Actions settings before rerunning. Never paste secret values into chat or commit them.
- The Node.js 20 message was a deprecation warning, not the cause of the failed job.
- Next: pass CI for this fix, configure the missing Actions values, rerun the smoke workflow, and verify upload/download/restore/cleanup. Do not switch to Candidate 5 or start training until storage and resume validation pass.


## Supabase smoke-test cleanup repair — 2026-11-19

- The live storage smoke test successfully uploaded a temporary checkpoint, verified its remote hash, downloaded it, and restored model plus optimizer tensors.
- The workflow then failed during cleanup verification. Supabase Storage listing is hierarchical: a directory entry is not an object, and deleting that directory name does not delete files nested below it.
- The smoke-test cleanup now recursively enumerates virtual folders, sends only actual object paths to Storage removal, and verifies that no objects remain under the unique run prefix.
- Added regression tests for nested model/optimizer shard folders, empty prefixes, and preserving objects belonging to another run.
- The first live run did not complete cleanup verification successfully. Treat its temporary prefix as potentially containing leftover test objects; the repair will be verified by CI and a fresh live smoke-test run.
- No production checkpoints were changed and no training was started.
- Next: pass PR checks, merge only after explicit approval, rerun the live smoke test, then verify cleanup and Candidate 5 save/restore plus interrupted-resume before considering training.


## Candidate 5 live interrupted-recovery validation — PR #67

- Added a manual-only GitHub Actions workflow: `.github/workflows/candidate5-live-recovery.yml`.
- The workflow runs the existing isolated recovery harness against the private Supabase `checkpoints` bucket using Candidate 5 (25,398,350 parameters), CPU precision `none`, and a bounded diagnostic sequence: two initial updates, checkpoint upload, a fresh-runtime restore, then one resumed update.
- It compares the resumed result against an uninterrupted reference: model weights, AdamW state, scheduler, data-stream position/RNG, curriculum, gradient scaler, and optimizer-to-model parameter binding.
- The test uses a unique temporary owner/run/checkpoint prefix. It does not write training status, touch production run IDs, acquire a production lease, or start a real training session.
- Recovery cleanup now recursively enumerates Supabase virtual folders, deletes only actual objects below the unique checkpoint prefix in batches, and verifies that the prefix is empty. Regression coverage models Supabase's immediate-child listing and null-ID virtual folders.
- The workflow requires the existing repository variable `SUPABASE_URL` (or the configured project URL fallback) and repository secrets `SUPABASE_SECRET_KEY` and `SUPABASE_OWNER_ID`. Never print or paste these credentials.
- The workflow is manual-only and is not invoked by pull-request CI. PR checks validate code and fake-storage behavior; the live workflow must be triggered manually after the PR is reviewed and merged.
- **No Kaggle or Composio integration is used. No real training has started.**
- A successful result validates this bounded recovery path against live Supabase; it does not establish training quality, long-run reliability, total remaining storage quota, or readiness for production training.

### Next steps

1. Pass all required pull-request checks and review the recovery/cleanup diff.
2. Merge only after the owner explicitly approves this PR.
3. Manually run `ULTRON Candidate 5 Live Interrupted Recovery` from GitHub Actions.
4. Inspect the structured report and verify every recovery assertion plus temporary-object cleanup.
5. Continue with math-data quality, duplicate/leakage controls, and held-out evaluation. Keep real training disabled until the full readiness checklist passes and the owner explicitly authorizes a first run.

## Recovery fault injection and mathematics dataset — PR #68

- PR #68 combines isolated Candidate 5 live-Supabase interrupted-recovery validation with a from-scratch mathematics dataset quality pipeline.
- Recovery tests are intentionally run after merge. The manual-only workflow injects a corrupted tensor component and a missing component under one unique temporary checkpoint prefix, requires both failures to be rejected, restores the valid component, and compares the next update from a fresh runtime against an uninterrupted reference. It checks model, optimizer, scheduler, data-stream/RNG, curriculum, scaler and optimizer-parameter binding, then verifies temporary-object cleanup.
- The mathematics generator covers 18 foundation topics. The deterministic generator rotates each topic through difficulty levels 1–3, and the independent verifier checks answers and solution steps. The deterministic solving agent and frozen evaluation fixture now cover all 18 topics.
- The dataset builder targets 110,000 examples: 100,000 train, 5,000 validation and 5,000 test. It reserves the canonical frozen evaluation examples in the test split, independently verifies examples, audits exact and near duplicates and cross-split leakage, checks topic/difficulty/split coverage, runs a fixed-seed reproducibility probe, and writes SHA-256 manifests.
- The manual-only dataset workflow builds the artifact and uploads it to GitHub Actions artifacts for 30 days. It does not start model training.
- Structural-template overlap is reported separately from near-duplicate leakage: the same problem form with different numeric values is not automatically treated as a leaked example.
- The 110,000-example corpus is an initial foundation dataset, not proof of target competence. It must be generated and its artifact/report inspected after merge before it is considered established.
- Pull-request CI does not use Supabase secrets. The live recovery test is manual-only and limited to a unique prefix in the existing private `checkpoints` bucket. No bucket, schema, RLS, Edge Function, secret or persistent production checkpoint is changed.
- No external AI API, pretrained weights, existing model, externally generated training data, or real training session is used.

### Post-merge actions

1. Run **ULTRON Candidate 5 Live Interrupted Recovery** and inspect every structured assertion, including corruption rejection, missing-component rejection, exact continuation and cleanup.
2. Run **ULTRON Build and Audit Mathematics Dataset** with the fixed seed. Inspect the manifest, all split counts, topic/difficulty coverage, duplicate/leakage report and held-out reservation.
3. Only after both post-merge tests pass, continue the separate readiness review. Keep real training disabled until the full readiness gates pass and the owner explicitly authorizes it.


## PR #68 review correction — Candidate 5 parameter count (2026-11-20)

The tokenizer vocabulary is now 80 characters after adding the semicolon and exponent caret required by generated mathematics examples. Candidate 5 therefore has **25,400,400 parameters** (dimension 512, 8 layers, 16 heads, feed-forward multiplier 4). The live Supabase interrupted-recovery script previously retained the pre-tokenizer-expansion expectation of 25,398,350, which would have caused the workflow to reject the correct model. Updated `scripts/verify_candidate5_supabase_recovery.py` to expect 25,400,400. This is a validation-only correction: it does not alter the architecture, weights, checkpoints, or training state. PR #68 remains unmerged pending fresh CI and review. No real training has started.


## Training-control 502 diagnostics hardening (2026-11-20)

- Investigated repeated authenticated `training-control` HTTP 502 responses. Supabase logs confirm the requests reached Edge Function version 1 with a valid authenticated session; the available request logs do not include the handler response body or enough runtime detail to prove whether the GitHub token is missing, invalid, or blocked by GitHub permissions.
- Added an owner-authenticated, read-only `health` action that reports only whether owner verification and the GitHub token are configured. It never returns secret values and never calls GitHub or dispatches a workflow.
- Missing `ULTRON_GITHUB_TOKEN` now returns HTTP 503 with a clear configuration message instead of being caught and mislabeled as HTTP 502.
- Unexpected GitHub/network failures now return a generic client-safe 502 while writing the error detail to Edge Function logs; upstream response details are no longer echoed to the browser.
- Added regression tests for owner-gated health diagnostics, secret-value non-disclosure, missing-token classification, and safe upstream errors.
- This code change does not create, rotate, or verify either production secret. The health action must be called by the signed-in owner after deployment. Do not enable Start until the health check confirms the token is configured and GitHub Status succeeds.
- No training was started; no model weights or checkpoints were touched.


## Training-control deployment and owner diagnostics (2026-11-20)

- PR #76 merged to `main` at `2fa68944ed90b338540a74437411920ac0b0263c` after all three required CI workflows passed.
- Deployed the merged `supabase/functions/training-control/index.ts` to Supabase project `euhmejpaswmdpsutbtse` as Edge Function version 2. The function inventory confirms status `ACTIVE` and `verify_jwt = true`.
- Version 2 adds an owner-authenticated, read-only `health` action. It reports only whether owner verification and the GitHub token are configured; it never returns secret values or calls GitHub.
- Missing `ULTRON_GITHUB_TOKEN` is classified as HTTP 503. Other upstream GitHub/network failures remain generic HTTP 502 responses, with diagnostic detail written to Edge Function logs.
- Deployment is verified, but the owner-only live health/status request has not yet been exercised in a browser session from this environment. The production secrets' presence and GitHub token permissions remain unverified. Do not press Start until the health check and GitHub Status both succeed.
- A follow-up dashboard change adds a **Check connection** control so the owner can run the health action without using developer tools. It must pass CI and be deployed to GitHub Pages before that button is available.
- No training was started; no weights or checkpoints were touched.

## Live training-control configuration diagnosis (2026-11-20)

- After PR #77 was deployed, the owner-session health request reached the training-control Edge Function version 2 but returned HTTP 503. Supabase request logs show the authenticated request was accepted by the platform; the response was generated by the function's preflight configuration guard, before the owner /auth/v1/user lookup and before the read-only health response.
- The previous guard combined two independent missing-configuration cases (SUPABASE_URL and ULTRON_OWNER_USER_ID) into one message. This did not identify which setting needed attention.
- Follow-up patch splits those checks and returns a distinct, safe setup message for each. It never returns a configured owner ID or any secret value.
- The first setting to verify in Supabase Dashboard → Edge Functions → Secrets is ULTRON_OWNER_USER_ID, whose value must exactly match the owner's Supabase Auth user UUID. SUPABASE_URL is normally supplied by the Edge Functions runtime; the revised error distinguishes it if it is absent.
- Secret values are not readable through the connected project tools. Their presence cannot be independently verified from this environment, and no secret was created, rotated, or exposed.
- Once the owner configuration is corrected and the updated function is deployed, run Check connection again. A successful health response then separately reports whether ULTRON_GITHUB_TOKEN is present. Only after that should GitHub Status be tested for token permissions.
- Do not weaken owner checks, place credentials in dashboard JavaScript, or start a compute workflow while configuration remains unverified. No model training or checkpoint changes occurred.


## Stage 3 — Diagnosis, teaching and researched Axiom Bank (baseline complete)

Merged PR: [#102](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/102), merge commit `c4b0ad688a7150ff07137c28b82b3460d3cdc22d`.

Implemented in this branch:
- Added `dashboard/math-tutor.js`: a session-only tutor with an 18-topic prerequisite graph, prerequisite readiness, weakest-topic selection, review-due prioritization, progressive hints from deterministic solver knowledge, independent final-answer checking, conservative mistake diagnosis, attempt/mastery/streak tracking and spaced review intervals of 1, 2, 4, 8 and 16 session turns.
- Mistake diagnosis explicitly refuses to infer a misconception from a wrong final answer alone. The tutor accepts optional written working, but this first release does not classify step-level error patterns and does not assign a misconception label.
- Adaptive practice selects topics only. Difficulty remains fixed at the existing foundation level; it is not represented as adaptive difficulty.
- Mastery and review state are held in memory only. No questions, answers, mastery history or learner profile are written to localStorage, Supabase, account history or training data.
- Added a searchable 37-entry Axiom Bank in `dashboard/axiom-bank.js` with formal-system scope, domain, formal statement, explanation, teaching note and research references. Initial coverage includes Peano natural-number axioms, field axioms, ordered-field axioms, real completeness, Euclid's five postulates, Kolmogorov probability axioms and ZFC set theory (including schemas and Choice). The catalog distinguishes primitive structure, individual axioms and axiom schemas.
- Added `docs/AXIOM_BANK_RESEARCH.md` describing sources, scope and limitations. The bank distinguishes primitive structures, axioms, schemas, definitions and theorems; it does not claim that the current rule-based solver derives its answers from formal axioms.
- Added the dashboard tutor and axiom-bank panels, responsive styles, search/details UI, Node tests and CI syntax checks. The tutor also surfaces up to three directly tagged axioms for each selected topic, with an explicit no-association state when none is catalogued.

Research sources used include University of Florida and Toho University Peano notes; UIC, Portland State and LibreTexts real-number/ordered-field notes; University of Glasgow and Euclid's Elements geometry references; Cambridge University Press and Boston University probability notes; and the Stanford Encyclopedia of Philosophy and TU Darmstadt ZFC notes. The detailed source URLs and findings are recorded in `docs/AXIOM_BANK_RESEARCH.md`.

Important boundaries:
- The Axiom Bank is a curated educational reference catalog, not yet a formal proof assistant. Its entries are accessible to the browser tutor as topic-scoped references; they are not used to train the neural model.
- A topic-to-axiom association is a teaching hint, not a machine-checked derivation.
- The existing structured reasoning kernel independently verifies final answers and deterministic replay; it does not formally prove intermediate natural-language steps.
- No model training, model-weight changes, dataset changes, checkpoint writes, Supabase deployment or external AI API use occurred.

Validation after merge: Python and Node test suites passed; preflight passed; training-prototype validation passed; Chromium and WebKit browser smoke tests passed; GitHub Pages build and deployment passed. The branch PR checks and main-branch checks were independently green. No model training was launched.

Stage 3 boundary: this is the safe baseline. Written work is accepted but not parsed into misconception classes yet; adaptive sequencing chooses topics, while difficulty remains fixed at foundation level. The axiom catalog is a researched educational reference linked into tutor practice, not a formal proof engine and not neural-model training data.

Next — Stage 4: design and implement a small auditable proof kernel. Define typed terms/formulas, explicit formal-system contexts, inference rules, proof objects, axiom/theorem references, and a checker that rejects invalid derivations. Add step-level work parsing only where the proof checker can validate it. Preserve the separation between Peano arithmetic, field/order/completeness, Euclidean geometry, probability and ZFC. Add negative tests for scope mixing, invalid substitutions, unsupported inference steps and forged proof traces. No actual model training until separately authorized.

## Stage 4 — Formal proof kernel (in progress)

**Overall project completion estimate: 32%.** This is a conservative project-wide estimate, not a claim that the neural model is trained or production-ready.

The Stage 4 first implementation adds:
- `dashboard/proof-kernel.js`: typed term/formula AST, seven isolated formal-system contexts, deterministic proof replay, and a deliberately small inference-rule set.
- Explicit executable Axiom Bank links for `PEANO-03` and `FIELD-01` only. Other bank entries remain educational references; schemas and unformalized statements cannot be invoked as proof rules.
- A browser proof-trace checker panel and a tutoring API that accepts structured traces only after replay validation.
- Rejection paths for malformed proofs, unknown/forward premises, duplicate IDs, wrong-system axioms, unsupported rules, forged conclusions, ill-typed expressions and variable-capture substitution.
- Adversarial JavaScript tests in `tests/proof_kernel.test.js`.
- Design and trust-boundary notes in `docs/FORMAL_PROOF_KERNEL.md`.

**Important limitations:** the checker is a small proof replayer, not a general theorem prover. It does not yet parse free-form working, handwriting, existential quantifiers, negation, induction, inequality arithmetic, geometric constructions, probability measure derivations or ZFC schemas. Universal introduction is intentionally withheld until eigenvariable side conditions are implemented. The seven contexts exist, but only Peano successor injectivity and real-field addition commutativity are currently executable axiom entries. A validated proof trace is evidence of a checked derivation, not an automatic misconception diagnosis.

**Training remains disabled.** No neural training, model-weight update, checkpoint mutation or dataset generation was performed.

### Next-chat handoff — continue Stage 4

1. Check PR for `feature/formal-proof-kernel`; run all required Python, JavaScript, preflight, Chromium and WebKit checks.
2. Fix every regression before merge. Do not bypass or weaken existing tests.
3. Review proof-kernel soundness carefully, especially assumption scoping, substitution, AST validation and cross-system axiom gating. Add tests for every discovered edge case.
4. Expand machine-formalized axioms incrementally, preserving exact Axiom Bank IDs and explicit system boundaries. Do not mark natural-language-only entries executable.
5. Add validated trace-to-step diagnostic rules only after the trace parser and checker can prove each transformation; otherwise abstain.
6. Keep the dashboard usable on iPad and Android. No training until the separate readiness gates and explicit authorization are satisfied.
7. Update this README at every meaningful milestone.

### Stage 4 first-slice merge and validation — 2026-11-21

- PR #103 merged by squash: `afa8181ff198d3f0b2524905d554967c45b267d3`.
- PR validation passed: Python/Node test suite, preflight, training-prototype validation, Chromium and WebKit.
- Main-commit validation also passed independently: test suite, preflight, Chromium, WebKit, Pages build and deployment.
- The initial JavaScript test run exposed two cross-context axiom error-code assertions. The checker was tightened to reject/report an unavailable axiom before attempting to type-check its foreign-system formula; the final run passed.
- The final proof checker also freezes the trusted context/axiom registries, enforces context-specific sorts, tracks open assumptions, rejects variable capture and keeps traces evidence-only until linked to the exercise's exact steps.
- The Stage 4 implementation is merged and deployed. Continue expanding the formal language and validated diagnostic mapping in separately reviewed PRs; do not overstate this first slice as a complete theorem prover.


## Stage 4 proof-kernel soundness follow-up — in progress (2026-11-21)

- Review of the merged proof kernel found that implication introduction checked the discharged assumption's formula but did not require that assumption to occur in the derived premise's dependency set. This could accept an invalid derivation of an implication from an unrelated assumption.
- The fix requires the discharged assumption ID to be present in the premise's tracked dependencies before implication introduction succeeds.
- Added a negative regression (unrelated assumption must be rejected) and a positive control (a genuinely used assumption may be discharged).
- Branch: `fix/proof-kernel-assumption-discharge`. Do not merge until the complete required CI suite and exact-diff review pass.
- Next: continue adversarial soundness review for strict AST shape validation, assumption scoping, substitution, premise arity, and dependency propagation. No training or checkpoint changes.


## Stage 4 proof-kernel strict-shape hardening — in progress (2026-11-21)

- Following the implication-discharge correction, the next audit slice makes the proof language closed-schema: term nodes, formula nodes, assumptions, proof envelopes, per-rule steps and working-trace envelopes reject unknown or missing fields.
- Added dense-array checks so sparse predicate arguments, assumptions, steps and premise lists cannot be silently skipped by JavaScript array iteration.
- Added negative regressions for injected AST/step/envelope properties, sparse premise and predicate arrays, sparse proof steps, and assumption metadata.
- The checks preserve the existing version-1 proof schema and inference rules. No new mathematical rule or axiom is enabled.
- Branch: `hardening/proof-kernel-strict-ast`. Do not merge until the full test suite, preflight, Training Prototype Validation, Chromium and WebKit checks pass and the exact diff is reviewed.
- No training, model-weight updates, dataset generation, checkpoint mutation or production changes.


## Stage 4 proof-kernel strict-shape hardening — in progress (2026-11-21)

- The next audit slice makes the proof language closed-schema: term nodes, formula nodes, assumptions, proof envelopes, per-rule steps and working-trace envelopes reject unknown or missing fields.
- Dense-array checks reject sparse predicate arguments, assumptions, steps and premise lists instead of allowing JavaScript array iteration to skip missing entries.
- Regression coverage checks injected AST/step/envelope properties, sparse premise and predicate arrays, sparse proof steps, invalid premise types, assumption metadata, and a null claimed conclusion.
- A present `claimedConclusion` is now always compared with the replayed result, including falsy values such as `null`.
- The existing version-1 AST and inference-rule set remains unchanged; this patch adds no axioms or proof rules.
- Branch: `hardening/proof-kernel-strict-ast`. Do not merge until full test suite, preflight, Training Prototype Validation, Chromium and WebKit pass and the exact diff is reviewed.
- No training, model-weight updates, dataset generation, checkpoint mutation or production changes.


## Stage 4 formal axiom expansion — in progress (2026-11-21)

- PR #104 merged as `a9277359ffba4e65f841bedab7b007cee16b61b5`: implication introduction now requires the discharged assumption to be present in the derived premise's dependency set.
- PR #105 merged as `d059afba4d45eae1ce84f878bac78fc7691d5bfa`: exact AST, proof-envelope, trace-envelope and per-rule step schemas; dense-array validation; strict claimed-conclusion comparison.
- Both PRs passed Test Suite, preflight, Training Prototype Validation, Chromium and WebKit on their reviewed PR heads.
- The next formalization increment adds PEANO-02 and FIELD-02, FIELD-03, FIELD-05, FIELD-06 and FIELD-09 using their exact Axiom Bank IDs. Negation is now representable as a typed formula, but no negation inference rules are enabled.
- PEANO-01 successor closure is enforced by the typed successor constructor; it is not misrepresented as a free-standing executable axiom. PEANO induction, field inverse/identity clauses needing unsupported conditions, and ordered-field, completeness, Euclidean, probability and ZFC entries remain non-executable.
- Branch: `feature/formalize-peano-and-field-axioms`. Merge only after code review and all required checks pass.
- No training, model-weight update, checkpoint mutation, dataset generation or production configuration change.


## Stage 4 — Peano induction schema — in progress (2026-11-21)

- PR #106 merged at `ee070248c99a03d83a58fbffb6b2afb69ea5c058`; executable PEANO-02/03 and FIELD-01/02/03/05/06/09 statements are bound to exact Axiom Bank IDs.
- This follow-up represents PEANO-04 as a dedicated schema-gated induction rule rather than pretending the schema is one finite axiom formula.
- The rule requires two backward-referenced premises: P(0) and ∀k(P(k)→P(S(k))). It constructs expected instances from the quantified conclusion, checks that the induction variable is fresh, and records PEANO-04 separately in usedAxiomSchemas.
- Added tests for valid induction, forged base cases, cross-system attempts, variable capture and schema-ID substitution.
- Induction is enabled only in the Peano context. No induction rule is enabled in field, geometry, probability, completeness or ZFC contexts.
- Branch: `feature/peano-induction-schema`. Do not merge until full Test Suite, preflight, Training Prototype Validation, Chromium and WebKit checks pass.
- No model training, dataset generation, weight/checkpoint mutation or production configuration change.
