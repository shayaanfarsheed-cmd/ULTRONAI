# ULTRONAI — Project status and handoff

**Repository:** [shayaanfarsheed-cmd/ULTRONAI](https://github.com/shayaanfarsheed-cmd/ULTRONAI)  
**Dashboard:** [GitHub Pages](https://shayaanfarsheed-cmd.github.io/ULTRONAI/)  
**Main branch:** `main`  
**Latest merged work:** PR #12 — dashboard performance optimization, merged at `02ddff7437f6a4ac89f78c52ceb36cef6d3f944b`.

## Current priorities

1. Finish and validate the dashboard/frontend before starting any model training.
2. Keep the website usable on iPad/iPhone, Android, and desktop browsers.
3. Harden owner/guest access and checkpoint handling without exposing secrets.
4. Keep all work within the $0 budget.

## Open pull requests

- **PR #13 — [Enforce checkpoint download limits while streaming](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/13)**  
  Branch: `fix/bounded-checkpoint-streams`; targets `main`; draft and unmerged. Adds bounded streaming checkpoint downloads, strict manifest step validation, and regression tests. CI trigger configuration was updated so Preflight and Training Prototype Validation also run on pull requests targeting feature branches. All three workflows passed on head `5fec2fdd7aacdfe62e0ba1e9dd6d53b96b237f49` (Preflight `44254731342`, Test Suite `44254731338`, Training Prototype Validation `44254731270`). This README sync creates a new commit; verify all checks again on the resulting exact head.

- **PR #14 — [Improve dashboard mobile accessibility and safe-area layout](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/14)**  
  Branch: `feature/mobile-dashboard-accessibility`; targets `main`; draft and unmerged. This branch was created from PR #13, so it contains PR #13's commits until #13 merges. Merge/review #13 first; then re-review #14's diff, which should reduce to its incremental dashboard changes. Current work adds a keyboard skip link, focus-visible outlines, selected-navigation semantics, safe-area spacing, narrow-screen layout refinements, and reduced-motion support. All three workflows were started on head `66a5000e633263c0b74289d5575c21dde36898c2`; rerun after this README update and verify the exact final head.

**Do not merge either PR until its exact final head has all required checks passing and the diff has been reviewed.** Real-device testing remains a separate requirement; automated CI does not prove iPad/iPhone compatibility.

## Product and security constraints

- Website first; no real training until the user explicitly approves it.
- $0 budget. No paid APIs, paid trials, billing setup, Kaggle, or phone-number-dependent setup.
- No external AI inference APIs, pretrained weights, existing models, or externally generated training data. ULTRON's model, data generator, and training code are independently implemented.
- No production Supabase schema, RLS, grants, storage, Edge Function, or secret changes without separate explicit approval.
- Never put privileged keys, service-role secrets, or passwords in browser code, notebooks, commits, or logs.
- Guest Mode is the public default. Owner sign-in is a single owner account; public self-registration is disabled.
- Frontend UUID checks and browser session storage are not backend authorization or secure credential storage. Private operations require server-side authorization and RLS.
- No owner provisioning, device pairing, agent installation, provider jobs, or live training without separate explicit approval.
- The RAM slider is a local preference only. It does not enforce a process or operating-system memory cap; a compatible device agent would need to enforce a safe limit.

## Model and training status

- The model is a from-scratch decoder-only Transformer with approximately 4.04 million trainable parameters, character-level tokenization, a 78-character vocabulary, 5 layers, embedding size 256, 8 attention heads, and context length 192 characters.
- The model is randomly initialized; it has no pretrained weights.
- The own data generator currently covers 14 topic areas, and an independent arithmetic verifier exists.
- Automated smoke tests validate implementation mechanics, not broad mathematical competence.
- **Actual model training has not started.** Passing tests do not mean the model has learned mathematics.
- Resolve the context-length difference against the older 1024-token target before changing architecture.

## Latest implementation notes

- PR #12 introduced bounded checkpoint metadata/file handling, concurrency controls, strict manifest checks, chart scheduling safeguards, and single-flight session refresh.
- PR #13 fixes the earlier post-allocation checkpoint size check by reading response streams incrementally, cancelling when the configured cap is exceeded, rejecting dishonest declared lengths, and failing closed when streaming is unavailable.
- The stream reader limits the retained response buffer, but buffer growth can temporarily hold old and new allocations; this is not a hard total browser-process memory cap.
- PR #14 improves keyboard navigation and mobile layout. These are code changes only, not proof from physical-device testing.

## Required validation

- Run all three GitHub Actions workflows on the exact final commit:
  - ULTRON preflight tests
  - ULTRON Test Suite
  - ULTRON Training Prototype Validation
- Review test logs and the complete PR diff; do not weaken tests or branch protection to obtain green checks.
- After code validation, test actual browsers/devices: iPad/iPadOS Safari and Chrome, iPhone, Android, and desktop; include narrow/wide layouts, refresh, interrupted network, guest/owner access, and keyboard/screen-reader navigation.
- Do not claim compatibility testing unless it was actually performed on the target devices.

## Next steps for the next session

1. Verify all three workflows on the latest exact heads of PR #13 and PR #14 after the README synchronization commits.
2. Fix any failures at their root cause and rerun validation after every source or README change.
3. Review PR #13 one final time; keep it draft until checks and review are complete.
4. After PR #13 is merged, review PR #14's now-reduced diff and validate it again.
5. Continue frontend implementation and device compatibility work. Do not start training yet.

