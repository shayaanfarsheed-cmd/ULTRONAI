import test, { before, after } from "node:test";
import assert from "node:assert/strict";
import { createHash, randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const SUPABASE_URL = process.env.SUPABASE_URL || "http://127.0.0.1:54321";
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const PUBLIC_KEY = process.env.SUPABASE_PUBLISHABLE_KEY || process.env.ANON_KEY;
const FUNCTION_URL = SUPABASE_URL + "/functions/v1/device-control";
const ORIGIN = "https://shayaanfarsheed-cmd.github.io";
const PASSWORD = "LocalPairingTest!2026";
const secrets = [];
let ipCounter = 1;
let owner;
let guest;
let ownerToken;
let guestToken;
let functionProcess;
let functionOutput = "";
let envDir;

const sha256 = value => createHash("sha256").update(value).digest("hex");
const testIp = () => "198.51.100." + ipCounter++;

async function adminRequest(path, options = {}) {
  const response = await fetch(SUPABASE_URL + path, {
    method: options.method || "GET",
    headers: {
      apikey: SERVICE_KEY,
      Authorization: "Bearer " + SERVICE_KEY,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  if (!response.ok) throw new Error("Local Supabase admin request failed (" + response.status + "): " + text);
  return data;
}

async function edgeRequest(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (options.token) headers.Authorization = "Bearer " + options.token;
  if (options.apikey !== false) headers.apikey = PUBLIC_KEY;
  if (options.ip) headers["cf-connecting-ip"] = options.ip;
  if (options.origin !== false) headers.Origin = ORIGIN;
  const response = await fetch(FUNCTION_URL + path, {
    method: options.method || "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  return { status: response.status, data };
}

async function createUser(label) {
  const email = "pairing-" + label + "-" + randomUUID() + "@example.test";
  const data = await adminRequest("/auth/v1/admin/users", {
    method: "POST",
    body: { email, password: PASSWORD, email_confirm: true },
  });
  return { id: data.id, email };
}

async function signIn(user) {
  const response = await fetch(SUPABASE_URL + "/auth/v1/token?grant_type=password", {
    method: "POST",
    headers: { apikey: PUBLIC_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email: user.email, password: PASSWORD }),
  });
  const data = await response.json();
  assert.equal(response.status, 200, "temporary local Auth user should sign in");
  return data.access_token;
}

async function createChallenge(token, address = testIp()) {
  const result = await edgeRequest("/challenge", { method: "POST", token, ip: address, body: {} });
  if (result.data.code) secrets.push(result.data.code);
  return result;
}

async function redeem(challengeId, code, address = testIp()) {
  const result = await edgeRequest("/redeem", {
    method: "POST",
    ip: address,
    body: { challenge_id: challengeId, code, device_name: "CI security test", platform: "linux", capabilities: {} },
  });
  if (result.data.device_token) secrets.push(result.data.device_token);
  return result;
}

async function dbGet(table, query) {
  const response = await fetch(SUPABASE_URL + "/rest/v1/" + table + "?" + query, {
    headers: { apikey: SERVICE_KEY, Authorization: "Bearer " + SERVICE_KEY },
  });
  assert.equal(response.status, 200, "service-role read of disposable test data should succeed");
  return response.json();
}

async function dbInsert(table, body) {
  const response = await fetch(SUPABASE_URL + "/rest/v1/" + table, {
    method: "POST",
    headers: {
      apikey: SERVICE_KEY,
      Authorization: "Bearer " + SERVICE_KEY,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  assert.equal(response.status, 201, "service-role insert into disposable test data should succeed: " + text);
  return JSON.parse(text);
}

async function waitForFunction() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (functionProcess.exitCode !== null) {
      throw new Error("Local Edge Function exited early: " + functionOutput);
    }
    try {
      const response = await fetch(FUNCTION_URL + "/devices", { headers: { apikey: PUBLIC_KEY } });
      if (response.status === 401) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error("Local Edge Function did not become ready: " + functionOutput);
}

before(async () => {
  assert.ok(SERVICE_KEY, "SUPABASE_SERVICE_ROLE_KEY is required");
  assert.ok(PUBLIC_KEY, "SUPABASE_PUBLISHABLE_KEY or ANON_KEY is required");
  owner = await createUser("owner");
  guest = await createUser("guest");
  ownerToken = await signIn(owner);
  guestToken = await signIn(guest);

  envDir = await mkdtemp(join(tmpdir(), "ultron-pairing-"));
  const envFile = join(envDir, ".env");
  await writeFile(envFile, [
    "SUPABASE_URL=" + SUPABASE_URL,
    "SUPABASE_SERVICE_ROLE_KEY=" + SERVICE_KEY,
    "ULTRON_OWNER_USER_ID=" + owner.id,
  ].join("\n") + "\n", { mode: 0o600 });

  functionProcess = spawn("supabase", [
    "functions", "serve", "device-control", "--no-verify-jwt", "--env-file", envFile,
  ], { env: process.env, stdio: ["ignore", "pipe", "pipe"] });
  functionProcess.stdout.on("data", chunk => { functionOutput += chunk.toString(); });
  functionProcess.stderr.on("data", chunk => { functionOutput += chunk.toString(); });
  await waitForFunction();
});

after(async () => {
  if (functionProcess && functionProcess.exitCode === null) {
    functionProcess.kill("SIGTERM");
    await new Promise(resolve => {
      const timer = setTimeout(resolve, 3000);
      functionProcess.once("exit", () => { clearTimeout(timer); resolve(); });
    });
  }
  for (const secret of secrets) {
    assert.ok(!functionOutput.includes(secret), "Edge Function logs must not contain pairing codes or device tokens");
  }
  for (const user of [owner, guest]) {
    if (user?.id) {
      await adminRequest("/auth/v1/admin/users/" + user.id, { method: "DELETE" }).catch(() => {});
    }
  }
  if (envDir) await rm(envDir, { recursive: true, force: true });
});

test("unauthenticated and non-owner users cannot access owner routes", async () => {
  assert.equal((await edgeRequest("/devices")).status, 401);
  assert.equal((await createChallenge(guestToken)).status, 401);
  assert.equal((await edgeRequest("/devices", { token: guestToken })).status, 401);
});

test("challenge hashes and concurrent redemption are single-use", async () => {
  const challenge = await createChallenge(ownerToken);
  assert.equal(challenge.status, 200);
  const { challenge_id: id, code } = challenge.data;
  assert.match(code, /^\d{8}$/);
  const rows = await dbGet("ultron_pairing_challenges", "select=code_hash&id=eq." + id);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].code_hash, sha256(code));
  assert.notEqual(rows[0].code_hash, code);

  const results = await Promise.all([redeem(id, code), redeem(id, code)]);
  assert.deepEqual(results.map(result => result.status).sort((a, b) => a - b), [201, 400]);
  const winner = results.find(result => result.status === 201);
  assert.ok(winner.data.device_id);
  assert.match(winner.data.device_token, /^[a-f0-9]{64}$/);
  const replay = await redeem(id, code);
  assert.equal(replay.status, 400);
  assert.equal("device_token" in replay.data, false);

  const devices = await dbGet("ultron_devices", "select=id,owner_id,token_hash&id=eq." + winner.data.device_id);
  assert.equal(devices.length, 1);
  assert.equal(devices[0].owner_id, owner.id);
  assert.equal(devices[0].token_hash, sha256(winner.data.device_token));
  assert.notEqual(devices[0].token_hash, winner.data.device_token);
});

test("five incorrect attempts lock the challenge", async () => {
  const challenge = await createChallenge(ownerToken);
  assert.equal(challenge.status, 200);
  const wrongCode = challenge.data.code === "00000000" ? "00000001" : "00000000";
  for (let i = 0; i < 5; i++) {
    assert.equal((await redeem(challenge.data.challenge_id, wrongCode)).status, 400);
  }
  assert.equal((await redeem(challenge.data.challenge_id, challenge.data.code)).status, 400);
  const rows = await dbGet("ultron_pairing_challenges", "select=attempts&id=eq." + challenge.data.challenge_id);
  assert.equal(rows[0].attempts, 5);
});

test("expired challenges cannot be redeemed", async () => {
  const id = randomUUID();
  const now = Date.now();
  await dbInsert("ultron_pairing_challenges", {
    id,
    owner_id: owner.id,
    code_hash: sha256("12345678"),
    created_at: new Date(now - 10 * 60_000).toISOString(),
    expires_at: new Date(now - 5 * 60_000).toISOString(),
  });
  assert.equal((await redeem(id, "12345678")).status, 400);
});

test("owner isolation, revocation, and revoked-token heartbeat rejection", async () => {
  const challenge = await createChallenge(ownerToken);
  assert.equal(challenge.status, 200);
  const paired = await redeem(challenge.data.challenge_id, challenge.data.code);
  assert.equal(paired.status, 201);

  assert.equal((await edgeRequest("/devices", { token: guestToken })).status, 401);
  assert.equal((await edgeRequest("/devices?id=" + paired.data.device_id, {
    method: "DELETE", token: guestToken,
  })).status, 401);

  const listed = await edgeRequest("/devices", { token: ownerToken });
  assert.equal(listed.status, 200);
  assert.ok(listed.data.devices.some(device => device.id === paired.data.device_id));

  const revoked = await edgeRequest("/devices?id=" + paired.data.device_id, {
    method: "DELETE", token: ownerToken,
  });
  assert.equal(revoked.status, 200);
  assert.equal(revoked.data.revoked, true);

  const heartbeat = await edgeRequest("/heartbeat", {
    method: "POST", token: paired.data.device_token, body: { capabilities: {} },
  });
  assert.equal(heartbeat.status, 401);
});

test("per-IP redemption limit allows ten requests and rejects the eleventh", async () => {
  const challenge = await createChallenge(ownerToken);
  assert.equal(challenge.status, 200);
  const address = testIp();
  const wrongCode = challenge.data.code === "00000000" ? "00000001" : "00000000";
  for (let i = 0; i < 10; i++) {
    assert.equal((await redeem(challenge.data.challenge_id, wrongCode, address)).status, 400);
  }
  assert.equal((await redeem(challenge.data.challenge_id, wrongCode, address)).status, 429);
});

test("per-IP challenge limit allows ten requests and rejects the eleventh", async () => {
  const address = testIp();
  for (let i = 0; i < 10; i++) {
    const result = await createChallenge(ownerToken, address);
    assert.equal(result.status, 200, "request " + (i + 1) + " should be allowed");
  }
  assert.equal((await createChallenge(ownerToken, address)).status, 429);
});
