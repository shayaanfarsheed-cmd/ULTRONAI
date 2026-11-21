# Supabase and private backend architecture

**Current website contract:** ULTRON's public GitHub Pages dashboard is account-free. It does not sign users in, restore browser sessions, access private training history, read or write checkpoints, upload user data, or call Supabase Auth/REST/Storage APIs. Its only network reads are the public repository's `servers.json` and `config.json` files.

## Public dashboard configuration

- `dashboard/config.js` is an empty compatibility stub and is not loaded by `dashboard/index.html`.
- No Supabase URL, publishable key, owner identifier, access token or refresh token is required by the public dashboard.
- `dashboard/app.js` clears stale legacy session/cache keys from older releases once, but never restores, creates or refreshes a session.
- Never put `sb_secret_...`, service-role credentials, device credentials, recovery tokens or private keys in any browser asset.

## Historical private backend resources

The repository has documented a Supabase project named `ultron-memory`, a `training_api` schema, owner-scoped RLS policies, lease/checkpoint RPCs and private Storage buckets. Those are historical repository records, not a fresh verification of live production state. Do not assume that live resources match the repository without a separately approved inspection.

The owner-gated `training-control` Edge Function and its server-side authorization code remain in the repository for controlled backend diagnostics. The public dashboard does not load `training-control.js`, does not expose its controls and does not dispatch its actions. Keep its origin checks, JWT verification, owner identity checks, least-privilege GitHub permissions and secret redaction intact. Do not deploy functions, run diagnostics or change production configuration as part of frontend cleanup.

## Legacy data-library SQL

`supabase/storage-setup.sql` documents an owner-scoped private `data-library` bucket. The corresponding upload, download, listing, search and deletion client has been removed from the public dashboard. The SQL is retained as historical backend documentation; it is not an active product feature and must not be applied or changed as part of this frontend work.

If the private bucket or policies already exist in production, preserve their private visibility and owner-scoped RLS. Do not make the bucket public or weaken policies. Do not assume the UI's removal deletes existing storage objects.

## Training credentials and compute

The training worker may require `SUPABASE_URL`, `SUPABASE_SECRET_KEY` and `SUPABASE_OWNER_ID`. These belong only in a trusted provider/runner secret manager. Never copy them into ChatGPT, browser storage, GitHub source files, notebook output or public configuration.

GitHub Actions CPU is the only planned remote training provider; Google Colab is manual-only. Any future provider change requires checking its current free-tier terms and resource limits. Budget remains $0.

No provider job, private diagnostic, migration, Edge Function deployment, checkpoint write or live training run is authorized by this document.

## Security invariants

- No public signup or owner-login UI.
- No browser token persistence or account-specific cache.
- No anonymous access to private tables, RPCs or Storage objects.
- Private backend operations remain server-authorized and fail closed.
- The public dashboard exposes no remote training start/stop or checkpoint controls.
- Keep server-side authorization, RLS and origin restrictions even when their browser client is absent.

## Prohibited actions

- Do not enable public signup or reintroduce owner login by assumption.
- Do not expose a Supabase secret/service-role key in browser code.
- Do not alter exposed schemas, grants, RLS policies, Storage policies, RPC permissions or production secrets.
- Do not deploy Edge Functions or migrations.
- Do not start training, pair a device, or launch a provider job.
- Do not add billing, paid trials, payment methods or quota workarounds.
