import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TrainingControlSecurityContractTests(unittest.TestCase):
    def test_edge_function_is_owner_gated_and_origin_restricted(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('const ALLOWED_ORIGIN = "https://shayaanfarsheed-cmd.github.io"', source)
        self.assertIn('user.id !== ownerId', source)
        self.assertIn('Deno.env.get("ULTRON_GITHUB_TOKEN")', source)
        self.assertNotIn("device-control", source)

    def test_missing_owner_configuration_has_specific_safe_errors(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        supabase_guard = source.index('if (!supabaseUrl)')
        owner_guard = source.index('if (!ownerId)')
        auth_lookup = source.index('const authResponse = await fetch')
        self.assertLess(supabase_guard, owner_guard)
        self.assertLess(owner_guard, auth_lookup)
        self.assertIn('Confirm the built-in SUPABASE_URL Edge Function environment setting.', source)
        self.assertIn('Add ULTRON_OWNER_USER_ID to Supabase Edge Function secrets', source)
        self.assertNotIn('ownerId: ownerId', source)
        self.assertNotIn('owner_id: ownerId', source)

    def test_github_actions_is_the_only_remote_launch_target(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('const CPU_SERVER_ID = "github_actions_cpu"', source)
        self.assertIn('id === CPU_SERVER_ID', source)
        self.assertIn('const CPU_WORKFLOW_PATH = "cpu-diagnostic.yml"', source)
        self.assertIn('"/actions/workflows/" + workflowPath + "/dispatches"', source)
        self.assertNotIn("lightning", source.lower())

    def test_public_dashboard_does_not_expose_remote_training_controls(self):
        html = (ROOT / "dashboard/index.html").read_text()
        self.assertNotIn('id="trainingStartButton"', html)
        self.assertNotIn('id="trainingStopButton"', html)
        self.assertNotIn('id="trainingRefreshButton"', html)
        self.assertNotIn('./training-control.js', html)

    def test_public_dashboard_has_no_owner_sign_in_or_private_navigation(self):
        html = (ROOT / "dashboard/index.html").read_text()
        nav = html.split('<nav class="side-nav"', 1)[1].split("</nav>", 1)[0]
        for forbidden in ("ownerSignInButton", "ownerSignOutButton"):
            self.assertNotIn(forbidden, html)
        for forbidden in ('data-view="data"', 'data-view="activity"', 'data-view="control"',
                          'data-view="devices"', 'data-view="checkpoints"'):
            self.assertNotIn(forbidden, nav)
        self.assertNotIn('id="ownerSignInDialog"', html)
        self.assertIn('class="connection-badge">PUBLIC</span>', html)

    def test_public_dashboard_does_not_restore_owner_sessions_or_cached_history(self):
        script = (ROOT / "dashboard/app.js").read_text()
        init = script.split("async function init()", 1)[1].split("document.addEventListener", 1)[0]
        self.assertIn("clearLegacyOwnerState();", init)
        self.assertIn("setAccessMode(false);", init)
        self.assertNotIn("loadSavedSession()", init)
        self.assertNotIn("verifyOwnerSession()", init)
        self.assertIn('sessionStorage.removeItem(SESSION_KEY)', script)
        self.assertIn('key.indexOf(CACHE_PREFIX) === 0', script)

    def test_launch_refreshes_status_after_busy_flag_is_cleared(self):
        script = (ROOT / "dashboard/training-control.js").read_text()
        launch = script.split("async function launch()", 1)[1].split("async function stop()", 1)[0]
        finally_block = launch.index("} finally {")
        refresh_call = launch.rindex("await refreshStatus();")
        self.assertGreater(refresh_call, finally_block)
        self.assertIn("busy = false;", launch[finally_block:refresh_call])

    def test_stop_confirmation_describes_diagnostic_without_checkpoint_claims(self):
        script = (ROOT / "dashboard/training-control.js").read_text()
        self.assertIn("Cancel the currently queued or running ULTRON CPU diagnostic?", script)
        self.assertIn("does not train the model or create, modify, or delete checkpoints", script)
        self.assertNotIn("latest durable checkpoint will be retained", script)

    def test_registry_exposes_only_github_actions_remote_and_manual_colab(self):
        import json
        servers = json.loads((ROOT / "servers.json").read_text())
        self.assertEqual([item["id"] for item in servers["servers"]], ["github_actions_cpu", "google_colab"])
        self.assertEqual(servers["servers"][0]["role"], "primary_cpu_runtime")
        self.assertFalse(servers["servers"][1]["remote_control_allowed"])


    def test_remote_dispatch_uses_actions_write_without_contents_write(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        workflow = (ROOT / ".github/workflows/cpu-diagnostic.yml").read_text()
        self.assertIn('"/actions/workflows/" + workflowPath + "/dispatches"', source)
        self.assertIn('ref: "main"', source)
        self.assertIn("Actions: write only", source)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("repository_dispatch:", workflow)

    def test_health_diagnostic_is_owner_gated_and_never_returns_secret_values(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        owner_check = source.index("if (user.id !== ownerId)")
        health_route = source.index('if (action === "health")')
        health_end = source.index("// Report missing integration configuration", health_route)
        health_block = source[health_route:health_end]
        self.assertLess(owner_check, health_route)
        self.assertIn("github_token_configured: Boolean(Deno.env.get(\"ULTRON_GITHUB_TOKEN\"))", health_block)
        self.assertNotIn("token:", health_block)
        self.assertIn('return safeError("GitHub integration is not configured.', source)
        self.assertIn('return safeError("GitHub integration is not configured. Add the server-side ULTRON_GITHUB_TOKEN secret.", 503, origin);', source)

    def test_readme_documents_current_training_control_deployment_and_live_gate(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("PR #80", readme)
        self.assertIn("version 5", readme)
        self.assertIn("workflow_dispatch", readme)
        self.assertIn("The deployed function source was fetched after deployment and matched", readme)
        self.assertIn("No diagnostic was launched and no model training was started.", readme)
        self.assertNotIn("version **3**", readme.split("## Latest verified status", 1)[1].split("## Authoritative model baseline correction", 1)[0])

    def test_training_status_responses_are_invalidated_after_owner_mode_changes(self):
        script = (ROOT / "dashboard/training-control.js").read_text()
        refresh = script.split("async function refreshStatus()", 1)[1].split("async function launch()", 1)[0]
        self.assertIn("const requestSequence = ++statusSequence;", refresh)
        self.assertIn("requestSequence !== statusSequence || !ownerSession()", refresh)
        self.assertIn('window.addEventListener("ultron:owner-mode-changed"', script)
        self.assertIn("statusSequence += 1;", script)
        self.assertIn('message(error.message, "error");', refresh)

    def test_invalid_expired_and_non_owner_sessions_fail_before_control_actions(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        credential_guard = source.index('if (!token || !apiKey)')
        auth_lookup = source.index('const authResponse = await fetch')
        invalid_session_guard = source.index('if (!authResponse.ok || !user.id)')
        non_owner_guard = source.index('if (user.id !== ownerId)')
        health_route = source.index('if (action === "health")')
        status_route = source.index('if (action === "status")')
        start_route = source.index('if (action === "start")')
        self.assertLess(credential_guard, auth_lookup)
        self.assertLess(auth_lookup, invalid_session_guard)
        self.assertLess(invalid_session_guard, non_owner_guard)
        self.assertLess(non_owner_guard, health_route)
        self.assertLess(health_route, status_route)
        self.assertLess(status_route, start_route)
        self.assertIn('return safeError("Your owner session is invalid or expired.", 401, origin);', source)
        self.assertIn('return safeError("Owner access is required for training operations.", 403, origin);', source)

    def test_control_function_rejects_untrusted_origins_and_methods(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        origin_guard = source.index('if (origin !== ALLOWED_ORIGIN)')
        options_guard = source.index('if (req.method === "OPTIONS")')
        method_guard = source.index('if (req.method !== "POST")')
        credential_guard = source.index('if (!token || !apiKey)')
        self.assertLess(origin_guard, options_guard)
        self.assertLess(options_guard, method_guard)
        self.assertLess(method_guard, credential_guard)
        self.assertIn('return safeError("Origin not allowed.", 403, ALLOWED_ORIGIN);', source)
        self.assertIn('return safeError("Method not allowed.", 405, origin);', source)
        self.assertIn('"Access-Control-Allow-Methods": "POST, OPTIONS"', source)
        self.assertNotIn('"Access-Control-Allow-Origin": "*"', source)

    def test_readme_records_live_training_control_version_six(self):
        readme = (ROOT / "README.md").read_text()
        latest = readme.split("## Latest verified status", 1)[1].split("\n## ", 1)[0]
        self.assertIn("PR [#96]", latest)
        self.assertIn("version 6", latest)
        self.assertIn("verify_jwt=true", latest)
        self.assertIn("source matches exactly", latest)
        self.assertIn("owner-only **Refresh status** from the signed-in owner's browser", latest)

    def test_training_control_rejects_non_object_and_malformed_request_bodies(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        size_guard = source.index("byteLength > MAX_BODY_BYTES")
        parse_request = source.index("parsed = JSON.parse(rawBody)")
        object_guard = source.index('if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))')
        action_guard = source.index('if (typeof requestBody.action !== "string")')
        server_guard = source.index('if (requestBody.server_id !== undefined && typeof requestBody.server_id !== "string")')
        health_route = source.index('if (action === "health")')
        self.assertLess(size_guard, parse_request)
        self.assertLess(parse_request, object_guard)
        self.assertLess(object_guard, action_guard)
        self.assertLess(action_guard, server_guard)
        self.assertLess(server_guard, health_route)
        self.assertIn('return safeError("Invalid JSON request.", 400, origin);', source)
        self.assertIn('return safeError("Unsupported action.", 400, origin);', source)
        self.assertIn('return safeError("Invalid server target.", 400, origin);', source)
        self.assertNotIn("body.action", source)
        self.assertNotIn("body.server_id", source)

    def test_readme_records_pr_96_and_current_owner_browser_gate(self):
        readme = (ROOT / "README.md").read_text()
        latest = readme.split("## Latest verified status", 1)[1].split("\n## ", 1)[0]
        self.assertIn("PR [#96]", latest)
        self.assertIn("397199389a1c829ff3107cff5560a2c27516fd9a", latest)
        self.assertIn("Deno type-check", latest)
        self.assertIn("owner-only **Refresh status** from the signed-in owner's browser", latest)
        self.assertIn("Keep actual training disabled", readme)

    def test_supabase_edge_function_is_typechecked_in_preflight(self):
        workflow = (ROOT / ".github/workflows/preflight-tests.yml").read_text()
        self.assertIn("uses: denoland/setup-deno@v2", workflow)
        self.assertIn("deno-version: v2.9.8", workflow)
        self.assertIn("deno check supabase/functions/training-control/index.ts", workflow)

    def test_github_token_secret_is_absent_from_all_dashboard_assets(self):
        for path in (
            ROOT / "dashboard" / "index.html",
            ROOT / "dashboard" / "app.js",
            ROOT / "dashboard" / "training-control.js",
            ROOT / "dashboard" / "config.js",
        ):
            self.assertNotIn("ULTRON_GITHUB_TOKEN", path.read_text(encoding="utf-8"))

    def test_upstream_failures_do_not_echo_upstream_details_to_clients(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('console.error("training-control request failed:", message);', source)
        self.assertIn("The control service could not complete the request.", source)
        self.assertNotIn("safeError(message.slice", source)


if __name__ == "__main__":
    unittest.main()
