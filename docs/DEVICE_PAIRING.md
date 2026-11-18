# ULTRON secure device pairing

## Current status

- The pairing migration is applied to the production Supabase project.
- The `device-control` Edge Function is deployed and active (version 2).
- The owner secret `ULTRON_OWNER_USER_ID` was reported configured by the owner; its value is not readable through connected tools.
- The dashboard feature flag remains **disabled**. No device has been paired and no training or remote command execution has started.
- The Python heartbeat-only agent is implemented for supported Linux, macOS, Windows, and server environments. The iPad browser is a dashboard/monitor and cannot host the persistent Python agent.

## Flow

1. An authenticated owner requests a pairing challenge.
2. The Edge Function creates an eight-digit code, stores only its SHA-256 hash, and returns the code once. It expires after five minutes.
3. The compatible agent redeems the challenge ID and code. A database transaction locks the challenge row, increments attempts, enforces the five-attempt limit, consumes it once, and creates a device record.
4. The agent receives a 256-bit random bearer credential once. Only its SHA-256 hash is stored. The Python agent holds the raw credential in memory only.
5. The agent sends heartbeats over outbound HTTPS. The dashboard can list and revoke devices.
6. Revocation changes device status; subsequent heartbeat requests are rejected.

## Security boundaries

- The browser never receives the service-role key or device bearer credential.
- Owner routes verify the Supabase access token using Auth `getUser()`, compare the verified UUID to the server-side `ULTRON_OWNER_USER_ID` secret, and derive `owner_id` from that verified user.
- Device registry, challenge, and rate-limit tables have RLS enabled and no direct grants to `anon` or `authenticated`; only the Edge Function service role accesses them.
- The challenge-consume function uses `SECURITY INVOKER`, is executable only by `service_role`, checks the verified service-role claim, locks the challenge row, expires and consumes codes atomically, and caps attempts.
- Pairing codes and device tokens are returned only in the relevant one-time response. The Edge Function does not log request bodies or credentials.
- CORS is restricted to the GitHub Pages origin. CORS is not authentication; owner/device credentials remain mandatory.
- Capabilities are untrusted metadata until independently validated by a future device agent.
- This API does not accept training commands, start training, acquire a training lease, or change checkpoints.

## Local integration test suite

The repository contains a disposable local Supabase test suite. It runs in GitHub Actions against a local Supabase stack; it does not connect to or modify production and requires no production credentials.

Coverage includes:

- Direct table and RPC access denied to browser roles.
- Wrong-code attempt counting and lockout after five attempts.
- Expired challenge rejection.
- Successful redemption and single-use behavior.
- Two concurrent redemption requests yielding exactly one successful device credential.
- Owner isolation using a second authenticated test user.
- Device revocation and rejection of subsequent heartbeats.
- Per-IP challenge endpoint rate limiting (10 allowed; the 11th rejected).
- SHA-256-only storage for challenge codes and device credentials, plus a check that local function logs do not contain test secrets.

Run locally with Docker, Node.js 22+, and the Supabase CLI:

```bash
supabase start
supabase test db
supabase status -o env
node --test tests/device_pairing.integration.test.mjs
supabase stop --no-backup
```

The integration test starts the local `device-control` Edge Function and creates temporary Auth users in the local stack. It does not require a second Supabase project.

## Production safeguards

- Keep `window.ULTRON_CONFIG.deviceControlEnabled` false until the local integration workflow passes and the production gateway behavior for `cf-connecting-ip` is independently confirmed.
- Never run challenge, revocation, or rate-limit destructive tests against production.
- Do not deploy test-only migrations or change production secrets as part of the CI workflow.
- Do not enable pairing or start training automatically after tests pass; that requires a separate reviewed change and explicit approval.
- Do not treat device-reported capabilities as trusted training eligibility.
- Do not put the device token in source code, browser storage, logs, or a committed file. Use the compute provider's encrypted secret manager or an OS credential vault for persistent storage.

## Known limitations

- No native iPad agent, OS keychain integration, device command channel, training control, or resource enforcement is included.
- Heartbeat capability payloads are not deeply schema-validated.
- The initial challenge code uses SHA-256. Its short expiry, five-attempt cap, and per-IP endpoint rate limit are required compensating controls.
- The local integration suite verifies rate-limit behavior when the trusted IP header is supplied. It cannot independently prove that the hosted Supabase gateway overwrites that header as expected; that production infrastructure behavior must be verified separately before enabling pairing.
