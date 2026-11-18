import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const OWNER_USER_ID = Deno.env.get("ULTRON_OWNER_USER_ID") || "";
const ALLOWED_ORIGIN = "https://shayaanfarsheed-cmd.github.io";
const corsHeaders = {
  "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Vary": "Origin",
};
const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});
function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: {
    ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store",
  }});
}
function randomHex(bytes: number) {
  const value = new Uint8Array(bytes);
  crypto.getRandomValues(value);
  return Array.from(value, (part) => part.toString(16).padStart(2, "0")).join("");
}
async function sha256(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (part) => part.toString(16).padStart(2, "0")).join("");
}
async function ownerFromRequest(request: Request) {
  const authorization = request.headers.get("Authorization") || "";
  const apiKey = request.headers.get("apikey") || "";
  if (!authorization.startsWith("Bearer ") || !apiKey) return null;
  const client = createClient(SUPABASE_URL, apiKey, {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await client.auth.getUser();
  return error || !data.user || !OWNER_USER_ID || data.user.id !== OWNER_USER_ID ? null : data.user;
}
async function allowPairingRequest(request: Request, endpoint: string, limit: number) {
  // Cloudflare overwrites cf-connecting-ip at the edge; do not trust arbitrary
  // client-provided forwarding headers as the rate-limit identity.
  const clientIp = request.headers.get("cf-connecting-ip") || "";
  if (!clientIp) return false;
  const keyHash = await sha256(endpoint + ":" + clientIp);
  const { data, error } = await admin.rpc("consume_ultron_pairing_rate_limit", {
    p_key_hash: keyHash, p_limit: limit, p_window_seconds: 60,
  });
  if (error) throw error;
  return data === true;
}

function validName(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.trim().length <= 80;
}
Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  const origin = request.headers.get("Origin");
  if (origin && origin !== ALLOWED_ORIGIN) return json({ error: "Origin not allowed." }, 403);
  const url = new URL(request.url);
  const route = url.pathname.split("/").filter(Boolean).slice(-1)[0] || "";
  try {
    if (request.method === "POST" && route === "challenge") {
      if (!(await allowPairingRequest(request, "challenge", 10))) return json({ error: "Pairing rate limit exceeded or client IP unavailable." }, 429);
      const owner = await ownerFromRequest(request);
      if (!owner) return json({ error: "Owner authentication required." }, 401);
      // Only one live challenge per owner; a newly issued code invalidates older ones.
      const { error: invalidateError } = await admin.from("ultron_pairing_challenges")
        .update({ consumed_at: new Date().toISOString() })
        .eq("owner_id", owner.id).is("consumed_at", null);
      if (invalidateError) throw invalidateError;
      const code = String(crypto.getRandomValues(new Uint32Array(1))[0] % 100000000).padStart(8, "0");
      const expiresAt = new Date(Date.now() + 5 * 60_000).toISOString();
      const { data, error } = await admin.from("ultron_pairing_challenges")
        .insert({ owner_id: owner.id, code_hash: await sha256(code), expires_at: expiresAt })
        .select("id,expires_at").single();
      if (error) throw error;
      return json({ challenge_id: data.id, code, expires_at: data.expires_at });
    }
    if (request.method === "POST" && route === "redeem") {
      if (!(await allowPairingRequest(request, "redeem", 10))) return json({ error: "Pairing rate limit exceeded or client IP unavailable." }, 429);
      const body = await request.json();
      const challengeId = String(body.challenge_id || "");
      const code = String(body.code || "");
      const deviceName = body.device_name;
      const platform = body.platform;
      const capabilities = body.capabilities && typeof body.capabilities === "object" ? body.capabilities : {};
      const platforms = ["windows", "macos", "linux", "other"];
      if (!/^[0-9a-f-]{36}$/i.test(challengeId) || !/^\d{8}$/.test(code) ||
          !validName(deviceName) || !platforms.includes(platform) || Array.isArray(capabilities) ||
          JSON.stringify(capabilities).length > 4096) return json({ error: "Invalid pairing payload." }, 400);
      const deviceToken = randomHex(32);
      const { data, error } = await admin.rpc("consume_ultron_pairing_challenge", {
        p_challenge_id: challengeId, p_code_hash: await sha256(code),
        p_device_name: deviceName.trim(), p_platform: platform,
        p_capabilities: capabilities, p_token_hash: await sha256(deviceToken),
      });
      if (error) throw error;
      if (!data) return json({ error: "Pairing code is invalid, expired, used, or locked." }, 400);
      return json({ device_id: data, device_token: deviceToken, token_type: "Bearer" }, 201);
    }
    if (request.method === "GET" && route === "devices") {
      const owner = await ownerFromRequest(request);
      if (!owner) return json({ error: "Owner authentication required." }, 401);
      const { data, error } = await admin.from("ultron_devices")
        .select("id,device_name,platform,capabilities,status,paired_at,last_seen_at,revoked_at")
        .eq("owner_id", owner.id).order("paired_at", { ascending: false }).limit(50);
      if (error) throw error;
      return json({ devices: data || [] });
    }
    if (request.method === "DELETE" && route === "devices") {
      const owner = await ownerFromRequest(request);
      if (!owner) return json({ error: "Owner authentication required." }, 401);
      const deviceId = url.searchParams.get("id") || "";
      const { data, error } = await admin.from("ultron_devices")
        .update({ status: "revoked", revoked_at: new Date().toISOString() })
        .eq("id", deviceId).eq("owner_id", owner.id).eq("status", "paired")
        .select("id").maybeSingle();
      if (error) throw error;
      if (!data) return json({ error: "Paired device not found." }, 404);
      return json({ revoked: true, device_id: data.id });
    }
    if (request.method === "POST" && route === "heartbeat") {
      const token = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/, "");
      if (!/^[a-f0-9]{64}$/.test(token)) return json({ error: "Device authentication required." }, 401);
      const body = await request.json().catch(() => ({}));
      const capabilities = body.capabilities && typeof body.capabilities === "object" ? body.capabilities : {};
      if (Array.isArray(capabilities) || JSON.stringify(capabilities).length > 4096) {
        return json({ error: "Invalid heartbeat capabilities." }, 400);
      }
      const { data, error } = await admin.from("ultron_devices")
        .update({ last_seen_at: new Date().toISOString(), capabilities: capabilities })
        .eq("token_hash", await sha256(token)).eq("status", "paired")
        .select("id").maybeSingle();
      if (error) throw error;
      if (!data) return json({ error: "Device credential is invalid or revoked." }, 401);
      return json({ accepted: true, device_id: data.id });
    }
    return json({ error: "Route not found." }, 404);
  } catch (error) {
    console.error("device-control request failed", error instanceof Error ? error.message : "unknown error");
    return json({ error: "Device control request failed." }, 500);
  }
});
