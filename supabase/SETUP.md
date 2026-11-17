# Supabase setup for ULTRON Training Control

The database migration is already applied to project \`ultron-memory\`. It creates only the \`training_api\` schema and its three tables. The existing six \`public\` memory tables were not changed.

## 1. Expose only the training schema

1. Open the Supabase dashboard and select \`ultron-memory\`.
2. Open **Settings → API → Data API**.
3. In **Exposed schemas**, remove \`public\` and any other schema that would expose unrelated tables.
4. Add \`training_api\`.
5. Save the settings.
6. Confirm the exposed schema list contains only \`training_api\`. That schema contains exactly \`training_status\`, \`server_log\`, and \`switch_requests\`.

Do not expose \`auth\`, \`storage\`, \`public\`, or any other schema for this project dashboard.

## 2. Create the private checkpoint bucket

The connected database tool cannot administer Supabase-managed Storage metadata because those tables are owned by Supabase's Storage service. Create the bucket through the dashboard:

1. Open **Storage**.
2. Choose **New bucket**.
3. Set the name to \`checkpoints\`.
4. Keep **Public bucket** turned off.
5. Set the file size limit to **45 MB**.
6. If MIME restrictions are shown, allow \`application/octet-stream\` and \`application/json\`.
7. Create the bucket.

The 45 MB bucket limit leaves headroom below the Free-plan 50 MB per-file limit. The checkpoint writer stores model weights, optimizer tensors, RNG state and JSON metadata as separate objects.

## 3. Add the owner-only download policy

1. In **Storage → Policies**, select the \`checkpoints\` bucket / \`storage.objects\`.
2. Create a policy for **SELECT** only.
3. Target role: \`authenticated\`.
4. Use this expression:

\`\`\`sql
bucket_id = 'checkpoints'
AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
\`\`\`

5. Save the policy.
6. Do not create INSERT, UPDATE or DELETE policies for \`anon\` or \`authenticated\`.

The notebook's Supabase secret key uses the service role and can write objects. The website uses only the publishable key and a signed-in user session; it can download only objects under that user's UUID folder.

Object paths use:

\`\`\`text
{owner_uuid}/{run_uuid}/{checkpoint_id}/{component_file}
\`\`\`

The matching SQL policy is kept in \`storage-policy.sql\` for reference. Create it through the Storage policy interface; do not try to alter Supabase-managed Storage table ownership.

## 4. Database permissions already installed

- RLS is enabled on all three \`training_api\` tables.
- Authenticated users can SELECT only rows whose \`owner_id\` equals \`auth.uid()\`.
- Authenticated users can insert only their own manual \`server_log\` entries and their own waiting \`switch_requests\`.
- Authenticated users can update only \`pause_requested\`, \`automatic_start_enabled\`, and \`server_statuses\` on their own \`training_status\` row.
- The service role has full table privileges and bypasses RLS.
- The existing six \`public\` memory tables and their policies were left unchanged.

## 5. Secret handling

Add the new Supabase secret key only to each cloud provider's secret manager as \`SUPABASE_SECRET_KEY\`. Never add it to this repository, notebook outputs, dashboard JavaScript, or browser storage.

The dashboard uses the public \`sb_publishable_...\` key only. A publishable key is designed to be public; the secret key is not.
