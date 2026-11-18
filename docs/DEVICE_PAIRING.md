# ULTRON secure device pairing

## Status

Control-plane and heartbeat-agent implementation is committed for review. It is not active until the database migration and Edge Function are separately approved and deployed; the dashboard feature flag remains off.

## Flow

1. An authenticated owner requests a pairing challenge.
2. The Edge Function creates an eight-digit cryptographically random code, stores only its SHA-256 hash, and returns the code once. It expires after five minutes.
3. The compatible agent redeems the challenge ID and code. A database transaction locks the challenge, increments attempts, enforces the five-attempt limit, consumes it once, and creates a device record.
4. The agent receives a 256-bit random bearer credential once. Only its SHA-256 hash is stored. The Python agent holds the raw credential in memory only. For restart recovery, the user may supply it through the compute provider's encrypted secret manager; never place it in source, logs, or browser storage.
5. The agent sends heartbeats over outbound HTTPS. The dashboard can list and revoke devices.
6. Revocation changes device status; subsequent heartbeat requests are rejected.

## Security boundaries

- The browser never receives the service-role key or device bearer credential.
- Owner routes verify the Supabase access token using Auth getUser(), compare the verified UUID to the server-side ULTRON_OWNER_USER_ID secret, and derive owner_id from that verified user.
- Device registry and challenge tables have RLS enabled and no grants to anon or authenticated; only the Edge Function service role accesses them.
- The consume function uses `SECURITY INVOKER`, is executable only by `service_role`, checks the verified service-role claim, locks the challenge row, expires and consumes codes atomically, and caps attempts. Only one active challenge is allowed per owner; issuing a new code invalidates the previous one.
- Pairing codes and device tokens are returned only in the relevant one-time response. The Edge Function does not log request bodies or credentials.
- CORS is restricted to the GitHub Pages origin. CORS is not authentication; owner/device credentials remain mandatory.
- Capabilities are untrusted metadata until independently validated by a future device agent.
- This API does not accept training commands, start training, acquire a training lease, or change checkpoints.

## Deployment prerequisites

1. Review supabase/migrations/20261118080000_device_pairing.sql.
2. Apply it to Supabase only after explicit production approval.
3. Deploy supabase/functions/device-control/index.ts as device-control.
4. Configure the Edge Function secret ULTRON_OWNER_USER_ID with the verified owner Auth UUID. SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are supplied by the Supabase Edge runtime. Owner Auth verification uses the public publishable apikey sent by the signed-in dashboard. Never put the service-role key in GitHub or browser code.
5. Review and test agents/device_agent.py on a supported Linux, macOS, or Windows device/server. The iPad is the dashboard/monitor, not a persistent Python agent host.
6. Verify the built-in 10 requests-per-minute per-IP limits for challenge creation and redemption against the Supabase gateway.
7. Run integration tests against a disposable Supabase project, including concurrent redemption, owner isolation (including a second authenticated user), expired/used codes, rate-limit windows, revocation, and credential redaction.

## Known limitations

- Control-plane foundation only. No native iPad agent, OS keychain integration, device command channel, training control, or resource enforcement is included.
- Heartbeat payloads are not yet deeply schema-validated. Do not treat reported capabilities as trusted for training eligibility.
- A device credential is a bearer token; production agent code must store it in the OS credential vault and support local credential deletion.
- The initial code uses SHA-256 for the eight-digit code. Keep the short expiry and attempt cap. Challenge creation and redemption are limited to 10 requests per minute per Cloudflare-provided client IP; only a hash of the IP plus endpoint label is stored. Confirm the gateway header behavior and rate-limit window using integration tests before production use.
- No migration or function has been deployed to production by this change.


## Device agent

A minimal Python agent is included at `agents/device_agent.py` for Linux, macOS, Windows, and compatible server environments. Set `ULTRON_SUPABASE_URL` and `ULTRON_PUBLISHABLE_KEY`, then run `python agents/device_agent.py --pair` and enter the challenge ID/code from the owner dashboard. The agent receives the device credential once, keeps it in memory, and sends a heartbeat every 60 seconds. It never prints or writes the raw credential to disk. To resume after a process restart, place the token in the compute provider's encrypted secret manager as `ULTRON_DEVICE_TOKEN`; do not paste it into source code or commit it.

The agent does not accept remote commands, run training, or change files. It only identifies itself and reports a small set of runtime metadata. The iPad can operate the owner dashboard, but iPadOS Safari/Chrome cannot host this persistent Python agent; iPad-native agent support would require a separate native application and is not included.
