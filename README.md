# ULTRONAI — Project status and handoff

**Repository:** [shayaanfarsheed-cmd/ULTRONAI](https://github.com/shayaanfarsheed-cmd/ULTRONAI)  
**Dashboard:** [GitHub Pages](https://shayaanfarsheed-cmd.github.io/ULTRONAI/)  
**Main branch:** `main`  
**Latest merged work:** PR #16 — verified owner authentication configuration, merged at `7b0dc262a2319c00253f106b9122efe13a388063`.

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

## Next steps for the next session

1. Verify the GitHub Pages deployment for merge commit `7b0dc262a2319c00253f106b9122efe13a388063`.
2. Test owner sign-in and Guest Mode in the deployed website; report the exact UI error if sign-in fails, but never share the password.
3. Verify private memory and checkpoint requests are correctly restricted by Supabase RLS and Storage policies.
4. Address the Supabase leaked-password-protection warning through the Supabase dashboard when authorized.
5. Continue dashboard UX and real-device testing. Do not start real training until the user explicitly approves it.


## Secure device pairing work package (PR in progress)

- Pairing control-plane source is being added on branch feature/secure-device-pairing.
- Proposed design: five-minute one-time pairing challenge, five attempts maximum, atomic single-use redemption, 256-bit per-device bearer credential stored hashed server-side, owner-scoped device listing and revocation, and outbound HTTPS heartbeats.
- Dashboard UI can request a one-time code and list/revoke devices after the Edge Function and migration are deployed.
- No database migration or Edge Function has been applied to production. No device agent exists yet; a code alone cannot connect a device until a compatible agent is implemented.
- Pairing does not start training or acquire the training lease. Device-reported capabilities are untrusted until validated by a future agent.
- Before production deployment, add edge/gateway per-IP throttling and disposable-project integration tests for concurrent redemption, expiry, attempt lockout, owner isolation, revocation, and secret redaction.


## Device pairing PR #18 — security review update

- Draft PR: [Build secure device pairing control plane](https://github.com/shayaanfarsheed-cmd/ULTRONAI/pull/18).
- Implements owner-only pairing challenge creation, one-time redemption, hashed device credentials, device registry/revocation, and heartbeat endpoint.
- Security review correction: Edge Function now checks the verified Auth user against `ULTRON_OWNER_USER_ID`; the database consume function uses `SECURITY INVOKER` and is executable only by service_role; a newly issued code invalidates older outstanding challenges; capability payloads must be JSON objects within the size limit.
- Pairing dashboard stays disabled unless `window.ULTRON_CONFIG.deviceControlEnabled === true`.
- Production deployment still requires explicit approval, migration application, Edge Function deployment, secrets (including the owner Auth UUID) configured in Supabase, and gateway/IP rate limiting.
- A compatible OS-level agent and disposable-project integration tests are not complete. The iPad browser cannot run this background agent; it can only act as the owner dashboard/monitor unless a native iPad app is later built.
- No production Supabase changes, device pairing, device commands, or training have occurred.
