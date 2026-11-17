# Supabase setup for ULTRON Training Control

Project: `ultron-memory` (`euhmejpaswmdpsutbtse`).

The training database schema and policies are installed. The private checkpoint bucket is also created and verified. The six existing `public` memory tables were not changed.

## 1. Expose only the training API schema

This is the remaining dashboard setting that must be changed manually:

1. Open the Supabase dashboard and select `ultron-memory`.
2. Open **Settings → API → Data API**.
3. In **Exposed schemas**, add `training_api`.
4. Remove `public` and any other schema from the exposed list.
5. Save the setting.
6. Confirm `training_api` is the only exposed schema.

The exposed schema contains exactly:
- `training_status`
- `server_log`
- `switch_requests`

Do not expose `auth`, `storage`, or any other schema. The Storage REST API works independently and does not require exposing the `storage` schema.

**Compatibility note:** removing `public` from the exposed list will stop any older browser application that directly calls the six `public` memory tables. The tables and their RLS policies remain intact; they are simply no longer reachable through the Data API.

## 2. Check the private checkpoint bucket

The `checkpoints` bucket has already been created.

Verified settings:
- Bucket ID: `checkpoints`
- Public: `false`
- Per-object limit: 45,000,000 bytes (45 MB)
- Allowed MIME types: `application/octet-stream`, `application/json`

The setup SQL is in `supabase/storage-setup.sql`.

## 3. Checkpoint access policy

The owner-only download policy has already been installed on `storage.objects`.

It allows a signed-in user to list/download objects only when the first folder is their Supabase Auth user UUID:

```sql
bucket_id = 'checkpoints'
AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
```

There are no `anon` or `authenticated` INSERT, UPDATE, or DELETE policies for this bucket. The notebook uses its backend secret key for uploads. The dashboard uses the publishable key plus the user's login session for downloads.

Object paths use:

```text
{owner_uuid}/{run_uuid}/{checkpoint_id}/{component_file}
```

## 4. Create your Supabase Auth account

The project currently has no Auth users. Before training:

1. Open **Authentication → Users**.
2. Create an email/password user, or sign up through the ULTRON dashboard once it is available.
3. Copy that user's **UID**. This is your `SUPABASE_OWNER_ID`.
4. Keep the UID as a configuration value; it is not an API secret.

The notebook uses this UUID to associate its run with your account. The database functions reject unknown owner IDs.

## 5. Create a backend secret key

1. Open **Settings → API Keys**.
2. Open **Publishable and secret API keys**.
3. Create a secret key beginning with `sb_secret_`.
4. Do not paste it into ChatGPT, GitHub source files, notebook cells, or browser code.

Add these values to each provider's secret manager:

| Name | Value |
|---|---|
| `SUPABASE_URL` | `https://euhmejpaswmdpsutbtse.supabase.co` |
| `SUPABASE_SECRET_KEY` | Your `sb_secret_...` key |
| `SUPABASE_OWNER_ID` | Your Auth user UUID |

The secret key is sent only in the `apikey` header. It is never sent as `Authorization: Bearer`.

Provider locations:
- Kaggle: **Add-ons → Secrets**
- Colab: **Secrets** panel (key icon)
- Lightning AI: Studio **Environment / Secrets**
- GitHub: Repository **Settings → Secrets and variables → Actions → New repository secret**

For GitHub Actions, add `SUPABASE_URL` as a repository variable if desired, and add `SUPABASE_SECRET_KEY` and `SUPABASE_OWNER_ID` as repository secrets.

## 6. Database permissions already installed

- RLS is enabled on all three `training_api` tables.
- Authenticated users can read only rows whose `owner_id` equals `auth.uid()`.
- The dashboard can update only the training control fields granted in SQL.
- Authenticated users can insert only their own manual server-log entries and waiting manual switch requests.
- The backend secret key uses the `service_role` database role and bypasses RLS.
- The five lease/checkpoint RPC functions are executable only by `service_role`; they use `SECURITY INVOKER`, not `SECURITY DEFINER`.
- Existing `public` memory tables and policies were left unchanged.

The SQL for the functions is in `supabase/lease-functions.sql`.

## 7. Rotate a leaked secret key

1. Open **Settings → API Keys**.
2. Create a replacement `sb_secret_...` key.
3. Update the provider secret in Kaggle, Colab, Lightning and GitHub Actions.
4. Run a connection check on the new key.
5. Delete the compromised key only after every backend has switched.

Secret-key rotation is independent of the publishable key. Never rotate by pasting either key into chat.
