# ULTRONAI — Project status and handoff

**Repository:** [shayaanfarsheed-cmd/ULTRONAI](https://github.com/shayaanfarsheed-cmd/ULTRONAI)  
**Dashboard:** [GitHub Pages](https://shayaanfarsheed-cmd.github.io/ULTRONAI/)  
**Main branch:** `main`  
**Latest merged work:** PR #14 — mobile accessibility and safe-area layout, merged at `b4f7209f4c9572f03e1fb221e9304ba0e211ba88`.

## Current priorities

1. Finish and validate the dashboard/frontend before starting any model training.
2. Keep the website usable on iPad/iPhone, Android, and desktop browsers.
3. Harden owner/guest access and checkpoint handling without exposing secrets.
4. Keep all work within the $0 budget.

## Recently merged work

- **PR #14 — [Improve dashboard mobile accessibility and safe-area layout](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/14)**  
  Merged on 2026-11-18 at `b4f7209f4c9572f03e1fb221e9304ba0e211ba88`. Final PR head: `b8b7e561c25797117a72ba24a2051854ac252267`. Added keyboard skip navigation, `aria-current` selected-navigation semantics, visible focus, iOS safe-area spacing including the sticky-header top inset, narrow-screen navigation refinements, reduced-motion support, landscape insets, touch targets, and regression coverage.
- All three required PR workflows passed on the exact final PR head: preflight, Test Suite, and Training Prototype Validation.
- GitHub Pages deployment and both main-branch workflows passed on merge commit `b4f7209f4c9572f03e1fb221e9304ba0e211ba88`.
- **Real-device compatibility testing is still outstanding.** Automated CI does not prove iPad/iPhone, Android, or desktop browser behavior.

## Product and security constraints

- Website first; no real training until the user explicitly approves it.
- $0 budget. No paid APIs, paid trials, billing setup, Kaggle, or phone-number-dependent setup.
- No external AI inference APIs, pretrained weights, existing models, or externally generated training data. ULTRON's model, data generator, and training code are independently implemented.
- No production Supabase schema, RLS, grants, storage, Edge Function, or secret changes without separate explicit approval.
- Never put privileged keys, service-role secrets, or passwords in browser code, notebooks, commits, or logs.
- Guest Mode is the public default. Owner sign-in is a single owner account; public self-registration is disabled.
- Frontend UUID checks and browser session storage are not backend authorization or secure credential storage. Private operations require server-side authorization and RLS.
- No owner provisioning, device pairing, agent installation, provider jobs, or live training without separate explicit approval.
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

## Required validation

The PR #14 automated workflows passed on the exact final PR head, and main-branch workflows plus GitHub Pages deployment passed on the merge commit. Do not treat automated checks as a substitute for real-device testing.

Next test actual iPad/iPadOS Safari and Chrome, iPhone, Android, and desktop browsers, including narrow/wide layouts, refresh, interrupted network, guest/owner access, and keyboard/screen-reader navigation. Do not claim device compatibility unless tested on those devices.

## Next steps for the next session

1. Test the deployed GitHub Pages dashboard on supported devices, starting with iPad/iPadOS.
2. Fix any issues found and add regression tests for reproducible defects.
3. Continue dashboard interaction, session, permission, and checkpoint UX validation.
4. Keep the website/frontend priority; do not start real training until the user explicitly approves it.
