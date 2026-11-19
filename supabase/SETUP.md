# Supabase and owner-access architecture

**Status (2026-11-18): owner-only cloud data library implementation is proposed on an unmerged branch. Its SQL has not been applied to production. Do not apply migrations or policy changes without separate explicit approval.**

## Product access model

ULTRON's accepted product design is:

- Exactly one intended owner account, with one identity across the website and private system operations.
- Guest Mode for public dashboard and public mathematics information.
- Guests cannot access private training history, checkpoints, device pairing, or remote training controls.
- Public self-registration must remain disabled. Owner provisioning must be restricted to the intended owner.
- Passwords must be handled by a trusted authentication provider and never stored in source code, browser storage, plaintext configuration, or notebooks.
- The browser must never receive a Supabase secret/service-role key.
- Private operations must derive the owner ID from a verified server-side identity. A browser-supplied owner ID is not authorization.

**Implementation status:** the current dashboard is public-mode only. The owner login, restricted owner provisioning, recovery flow, and backend authorization boundary are not implemented. Do not treat the legacy instructions in earlier project notes as live setup steps.

## Existing Supabase resources — historical repository documentation

The repository documents an existing Supabase project named `ultron-memory` with project reference `euhmejpaswmdpsutbtse`. The repository also documents an existing `training_api` schema, owner-scoped RLS policies, lease/checkpoint RPCs, and a private `checkpoints` Storage bucket.

These statements describe the last repository inspection; they are not a fresh live verification. Do not assume the live project still matches them without a separately approved inspection.

Existing training API tables documented by the repository:
- `training_status`
- `server_log`
- `switch_requests`

Existing lease/fencing and checkpoint functions must remain the sole authoritative training-writer mechanism. Device control must not create a competing lease.

## Safe browser configuration

- `dashboard/config.js` may contain only the project URL and publishable/anon key.
- A publishable key is public and does not authenticate the owner.
- Never place `sb_secret_...`, service-role credentials, device credentials, pairing codes, recovery tokens, or private keys in the dashboard.
- The current publishable-key value is a placeholder. Do not ask the user to paste a key into chat.

## Future owner authentication work package

Before owner login is implemented, the design and tests must cover:

1. One intended owner identity; no public self-registration.
2. Secure login and logout.
3. Secure password recovery.
4. Session expiry, refresh, revocation and multi-device access.
5. Server-side authorization on every private operation.
6. Anonymous Guest Mode denial for all private tables, RPCs, storage objects and device endpoints.
7. Cross-owner isolation and attempts to spoof owner IDs.
8. Rate limiting, audit events, secret redaction and account recovery abuse cases.

The exact provisioning mechanism must be selected before implementation. Do not enable an open signup endpoint and rely on hiding the signup button.

## Future device-control backend

Device registry, one-time expiring pairing challenges, per-device credentials, command queue, heartbeat and revocation are not present in the inspected repository. They require a separate non-public control plane and narrow trusted server endpoints.

- Keep device-control records out of browser-exposed schemas.
- Do not grant anonymous users access to device records or privileged RPCs.
- Authenticate the agent independently from the owner.
- Derive owner/device relationships on the server.
- Use atomic command claim and idempotent acknowledgement.
- Validate command expiry, nonce, action allowlist, payload size and current fencing token.
- Reuse the existing training lease/fencing design.
- Keep checkpoint storage private and verify SHA-256 before restore.

No migration SQL or Edge Function deployment is authorized by this guide.

## Provider and training secrets

The training worker may require environment secrets such as `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `SUPABASE_OWNER_ID`. These belong only in a trusted provider/runner secret manager. They are not website configuration and must never be copied into ChatGPT, GitHub source files, notebook output, or browser storage.

GitHub Actions CPU is the only remote training provider. Google Colab is manual-only. Any future provider change requires confirmation that it is genuinely free, needs no payment method, and complies with published limits. Budget remains $0.

No provider job or live training run may start without separate explicit approval.

## What not to do

- Do not follow legacy instructions to create an unrestricted Supabase Auth account.
- Do not enable public signup.
- Do not alter exposed schemas, grants, RLS policies, Storage policies, RPC permissions, or production secrets.
- Do not deploy Edge Functions or migrations.
- Do not start training, pair a device, or launch a provider job.
- Do not add billing, a payment method, paid trials, or quota workarounds.



## Owner-only shared data library (proposed)

The dashboard branch `feature/owner-data-library-sync` adds a private Supabase Storage bucket named `data-library`. Each object path is `<verified-owner-auth-uuid>/<filename>`. The SQL in `storage-setup.sql` creates the private bucket (20 MiB per file) and owner-folder SELECT, INSERT, UPDATE, and DELETE policies based on `auth.uid()`. No anonymous or guest policy is created.

Every browser must sign in to the same owner account. The dashboard lists the cloud bucket and refreshes every 20 seconds while visible, so changes propagate to other signed-in browsers. This is polling-based sync, not instantaneous push. The UI stores uploaded bytes as opaque data and never executes them or starts training. The SQL remains unapplied until separately approved.
