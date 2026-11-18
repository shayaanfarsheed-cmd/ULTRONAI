# ULTRON secure device pairing

## Status

Reviewed implementation proposal only. It is not active until the database migration and Edge Function are separately approved and deployed. The device agent is not included.

## Flow

1. An authenticated owner requests a pairing challenge.
2. The Edge Function creates an eight-digit cryptographically random code, stores only its SHA-256 hash, and returns the code once. It expires after five minutes.
3. The compatible agent redeems the challenge ID and code. A database transaction locks the challenge, increments attempts, enforces the five-attempt limit, consumes it once, and creates a device record.
4. The agent receives a 256-bit random bearer credential once. Only its SHA-256 hash is stored. The agent must keep the raw credential in its operating system credential store; never in source, logs, or browser storage.
5. The agent sends heartbeats over outbound HTTPS. The dashboard can list and revoke devices.
6. Revocation changes device status; subsequent heartbeat requests are rejected.

## Security boundaries

- The browser never receives the service-role key or device bearer credential.
- Owner routes verify the Supabase access token using Auth getUser() and derive owner_id from that verified user.
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
4. Configure Edge Function secrets SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY in Supabase secrets. Never put the service-role key in GitHub or browser code.
5. Implement and security-review a compatible device agent before enabling pairing in the dashboard.
6. Add rate limiting at the Edge Function/gateway layer before public deployment. The database caps guesses per challenge; it does not replace per-IP throttling.
7. Add gateway/IP-level rate limiting and integration tests against a disposable Supabase project, including concurrent redemption, owner isolation (including a second authenticated user), expired/used codes, revocation, and credential redaction.

## Known limitations

- Control-plane foundation only. No agent installer, OS keychain integration, device command channel, training control, or resource enforcement is included.
- Heartbeat payloads are not yet deeply schema-validated. Do not treat reported capabilities as trusted for training eligibility.
- A device credential is a bearer token; production agent code must store it in the OS credential vault and support local credential deletion.
- The initial code uses SHA-256 for the eight-digit code. Keep the short expiry and attempt cap; add edge-level IP throttling before production use.
- No migration or function has been deployed to production by this change.
