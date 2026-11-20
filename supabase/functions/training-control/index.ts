const ALLOWED_ORIGIN = "https://shayaanfarsheed-cmd.github.io";
const REPOSITORY = "shayaanfarsheed-cmd/ULTRONAI";
const CPU_WORKFLOW_PATH = "cpu-diagnostic.yml";
const CPU_SERVER_ID = "github_actions_cpu";
const MAX_BODY_BYTES = 4096;
function response(body: unknown, status = 200, origin = ALLOWED_ORIGIN) {
  return new Response(JSON.stringify(body), { status, headers: {
    "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
    "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Vary": "Origin",
  }});
}
function safeError(message: string, status: number, origin: string) { return response({ ok: false, error: message }, status, origin); }
async function githubRequest(path: string, method = "GET", body?: unknown) {
  const token = Deno.env.get("ULTRON_GITHUB_TOKEN");
  if (!token) throw new Error("Server configuration is incomplete: GitHub token is missing.");
  const result = await fetch("https://api.github.com" + path, { method, headers: {
    "Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
    "X-GitHub-Api-Version": "2022-11-28", ...(body ? { "Content-Type": "application/json" } : {}),
  }, body: body ? JSON.stringify(body) : undefined });
  if (!result.ok) {
    const detail = await result.json().catch(() => ({}));
    if (result.status === 401 || result.status === 403) throw new Error("GitHub rejected the server credential or its repository permissions.");
    if (result.status === 404) throw new Error("The configured GitHub workflow was not found.");
    throw new Error("GitHub request failed (" + result.status + "): " + String(detail.message || "unknown error").slice(0, 180));
  }
  return result.status === 204 || result.status === 202 ? null : await result.json();
}
async function listRuns(workflowPath: string) {
  const data = await githubRequest("/repos/" + REPOSITORY + "/actions/workflows/" + workflowPath + "/runs?per_page=10") as { workflow_runs?: Array<Record<string, unknown>> };
  return Array.isArray(data.workflow_runs) ? data.workflow_runs : [];
}
function summarizeRun(run: Record<string, unknown> | undefined, fallbackName: string) {
  if (!run) return null;
  return { id: run.id, name: run.name || run.display_title || fallbackName, status: run.status,
    conclusion: run.conclusion, html_url: run.html_url, created_at: run.created_at,
    updated_at: run.updated_at, event: run.event };
}
async function dispatchWorkflow(workflowPath: string) {
  // Use workflow_dispatch so the fine-grained token needs Actions: write only.
  // repository_dispatch requires Contents: write, which is intentionally not granted.
  await githubRequest("/repos/" + REPOSITORY + "/actions/workflows/" + workflowPath + "/dispatches", "POST", {
    ref: "main",
  });
}
Deno.serve(async (req: Request) => {
  const origin = req.headers.get("Origin") || "";
  if (origin !== ALLOWED_ORIGIN) return safeError("Origin not allowed.", 403, ALLOWED_ORIGIN);
  if (req.method === "OPTIONS") return response({ ok: true }, 200, origin);
  if (req.method !== "POST") return safeError("Method not allowed.", 405, origin);
  const authHeader = req.headers.get("Authorization") || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  const apiKey = req.headers.get("apikey") || "";
  if (!token || !apiKey) return safeError("A signed-in owner session is required.", 401, origin);
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const ownerId = Deno.env.get("ULTRON_OWNER_USER_ID");
  if (!supabaseUrl) return safeError("Supabase Auth verification is not configured. Confirm the built-in SUPABASE_URL Edge Function environment setting.", 503, origin);
  if (!ownerId) return safeError("Owner verification is not configured. Add ULTRON_OWNER_USER_ID to Supabase Edge Function secrets; do not place its value in the website or a chat.", 503, origin);
  try {
    const authResponse = await fetch(supabaseUrl.replace(/\/$/, "") + "/auth/v1/user", { headers: { "apikey": apiKey, "Authorization": authHeader } });
    const user = await authResponse.json().catch(() => ({}));
    if (!authResponse.ok || !user.id) return safeError("Your owner session is invalid or expired.", 401, origin);
    if (user.id !== ownerId) return safeError("Owner access is required for training operations.", 403, origin);
    const rawBody = await req.text();
    if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) return safeError("Request is too large.", 413, origin);
    let parsed: unknown;
    try { parsed = JSON.parse(rawBody); } catch { return safeError("Invalid JSON request.", 400, origin); }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return safeError("Invalid JSON request.", 400, origin);
    }
    const requestBody = parsed as { action?: unknown; server_id?: unknown };
    if (typeof requestBody.action !== "string") return safeError("Unsupported action.", 400, origin);
    if (requestBody.server_id !== undefined && typeof requestBody.server_id !== "string") {
      return safeError("Invalid server target.", 400, origin);
    }
    const action = requestBody.action;
    const serverId = requestBody.server_id as string | undefined;

    // This read-only diagnostic is owner-gated and never contacts GitHub or reveals secret values.
    if (action === "health") {
      return response({ ok: true, checks: {
        owner_verification_configured: true,
        github_token_configured: Boolean(Deno.env.get("ULTRON_GITHUB_TOKEN")),
        remote_target: CPU_SERVER_ID,
        workflow: CPU_WORKFLOW_PATH,
      } }, 200, origin);
    }
    // Report missing integration configuration explicitly instead of misclassifying it as an upstream 502.
    if (!Deno.env.get("ULTRON_GITHUB_TOKEN")) {
      return safeError("GitHub integration is not configured. Add the server-side ULTRON_GITHUB_TOKEN secret.", 503, origin);
    }

    if (action === "status") {
      const id = serverId || CPU_SERVER_ID;
      if (id !== CPU_SERVER_ID) return safeError("Unsupported server status target.", 400, origin);
      const runs = await listRuns(CPU_WORKFLOW_PATH);
      return response({ ok: true, run: summarizeRun(runs[0], "ULTRON CPU Diagnostic") }, 200, origin);
    }
    if (action === "start") {
      const id = serverId || CPU_SERVER_ID;
      const workflowPath = id === CPU_SERVER_ID ? CPU_WORKFLOW_PATH : "";
      if (!workflowPath) return safeError("That provider does not have a remote launch adapter.", 409, origin);
      const cpuRuns = await listRuns(CPU_WORKFLOW_PATH);
      const active = cpuRuns.find(run => run.status === "queued" || run.status === "in_progress");
      if (active) return response({ ok: false, error: "Another ULTRON remote launch workflow is already queued or running.", run: summarizeRun(active, "ULTRON CPU Diagnostic") }, 409, origin);
      await dispatchWorkflow(workflowPath);
      return response({ ok: true, accepted: true, message: "GitHub Actions accepted the safe CPU diagnostic request. It measures runner resources and installs CPU PyTorch; it does not start training or touch checkpoints." }, 202, origin);
    }
    if (action === "stop") {
      const id = serverId || CPU_SERVER_ID;
      if (id !== CPU_SERVER_ID) return safeError("Unsupported stop target.", 400, origin);
      const runs = await listRuns(CPU_WORKFLOW_PATH);
      const active = runs.find(run => run.status === "queued" || run.status === "in_progress");
      if (!active || !Number.isSafeInteger(Number(active.id))) return response({ ok: true, stopped: false, message: "No queued or running ULTRON CPU workflow was found." }, 200, origin);
      await githubRequest("/repos/" + REPOSITORY + "/actions/runs/" + String(active.id) + "/cancel", "POST");
      return response({ ok: true, stopped: true, run_id: active.id }, 200, origin);
    }
    return safeError("Unsupported action.", 400, origin);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected server error.";
    console.error("training-control request failed:", message);
    return safeError("The control service could not complete the request. Check the owner-only health diagnostic and Edge Function logs.", 502, origin);
  }
});
