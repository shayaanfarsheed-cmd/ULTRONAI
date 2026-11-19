const ALLOWED_ORIGIN = "https://shayaanfarsheed-cmd.github.io";
const REPOSITORY = "shayaanfarsheed-cmd/ULTRONAI";
const WORKFLOW_PATH = "cpu-training.yml";
const LAUNCHABLE_SERVER = "github_actions_cpu";
const MAX_BODY_BYTES = 4096;

function response(body: unknown, status = 200, origin = ALLOWED_ORIGIN) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "authorization, apikey, content-type",
      "Vary": "Origin",
    },
  });
}

function safeError(message: string, status: number, origin: string) {
  return response({ ok: false, error: message }, status, origin);
}

async function githubRequest(path: string, method = "GET", body?: unknown) {
  const token = Deno.env.get("ULTRON_GITHUB_TOKEN");
  if (!token) throw new Error("Server configuration is incomplete: GitHub token is missing.");
  const result = await fetch("https://api.github.com" + path, {
    method,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + token,
      "X-GitHub-Api-Version": "2022-11-28",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!result.ok) {
    const detail = await result.json().catch(() => ({}));
    if (result.status === 401 || result.status === 403) {
      throw new Error("GitHub rejected the server credential or its repository permissions.");
    }
    if (result.status === 404) throw new Error("The configured GitHub workflow was not found.");
    throw new Error("GitHub request failed (" + result.status + "): " +
      String(detail.message || "unknown error").slice(0, 180));
  }
  return result.status === 204 ? null : await result.json();
}

async function listRuns() {
  const data = await githubRequest(
    "/repos/" + REPOSITORY + "/actions/workflows/" + WORKFLOW_PATH + "/runs?per_page=10"
  ) as { workflow_runs?: Array<Record<string, unknown>> };
  return Array.isArray(data.workflow_runs) ? data.workflow_runs : [];
}

function summarizeRun(run: Record<string, unknown> | undefined) {
  if (!run) return null;
  return {
    id: run.id,
    name: run.name || run.display_title || "ULTRON CPU Training",
    status: run.status,
    conclusion: run.conclusion,
    html_url: run.html_url,
    created_at: run.created_at,
    updated_at: run.updated_at,
    event: run.event,
  };
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
  if (!supabaseUrl || !ownerId) {
    return safeError("Owner verification is not configured. Launch controls are disabled.", 503, origin);
  }

  try {
    const authResponse = await fetch(supabaseUrl.replace(/\/$/, "") + "/auth/v1/user", {
      headers: { "apikey": apiKey, "Authorization": authHeader },
    });
    const user = await authResponse.json().catch(() => ({}));
    if (!authResponse.ok || !user.id) return safeError("Your owner session is invalid or expired.", 401, origin);
    if (user.id !== ownerId) return safeError("Owner access is required for training operations.", 403, origin);

    const rawBody = await req.text();
    if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
      return safeError("Request is too large.", 413, origin);
    }
    let body: { action?: string; server_id?: string };
    try { body = JSON.parse(rawBody); } catch { return safeError("Invalid JSON request.", 400, origin); }

    if (body.action === "status") {
      const runs = await listRuns();
      return response({ ok: true, run: summarizeRun(runs[0]) }, 200, origin);
    }

    if (body.action === "start") {
      if (body.server_id !== LAUNCHABLE_SERVER) {
        return safeError("That provider is manual-only. Select GitHub Actions CPU to launch remotely.", 409, origin);
      }
      const runs = await listRuns();
      const active = runs.find((run) => run.status === "queued" || run.status === "in_progress");
      if (active) return response({ ok: false, error: "A ULTRON workflow is already queued or running.", run: summarizeRun(active) }, 409, origin);

      const requestId = crypto.randomUUID();
      await githubRequest("/repos/" + REPOSITORY + "/dispatches", "POST", {
        event_type: "ultron-cpu-start",
        client_payload: {
          request_id: requestId,
          server_id: LAUNCHABLE_SERVER,
          requested_at: new Date().toISOString(),
        },
      });
      return response({
        ok: true,
        accepted: true,
        request_id: requestId,
        message: "GitHub Actions accepted the launch request. The workflow may take a short time to appear.",
      }, 202, origin);
    }

    if (body.action === "stop") {
      const runs = await listRuns();
      const active = runs.find((run) => run.status === "queued" || run.status === "in_progress");
      if (!active || !Number.isSafeInteger(Number(active.id))) {
        return response({ ok: true, stopped: false, message: "No queued or running ULTRON workflow was found." }, 200, origin);
      }
      await githubRequest("/repos/" + REPOSITORY + "/actions/runs/" + String(active.id) + "/cancel", "POST");
      return response({ ok: true, stopped: true, run_id: active.id }, 200, origin);
    }

    return safeError("Unsupported action.", 400, origin);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected server error.";
    return safeError(message.slice(0, 240), 502, origin);
  }
});
