import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


class DashboardStaticTests(unittest.TestCase):
    def test_dashboard_runtime_behaviour(self):
        result = subprocess.run(
            ["node", "--test", str(ROOT / "tests" / "dashboard_runtime.test.js")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_training_control_status_race_behaviour(self):
        result = subprocess.run(
            ["node", "--test", str(ROOT / "tests" / "dashboard_training_control.test.js")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_browser_math_agent_behaviour(self):
        result = subprocess.run(
            ["node", "--test", str(ROOT / "tests" / "math_agent.test.js")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_math_agent_view_is_public_bounded_and_explicit_about_training(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        agent = (DASHBOARD / "math-agent.js").read_text(encoding="utf-8")
        self.assertIn('data-view="math"', html)
        self.assertIn('id="view-math"', html)
        self.assertIn('id="mathAgentForm"', html)
        self.assertIn('id="mathStartButton"', html)
        self.assertIn('id="mathStopButton"', html)
        self.assertIn('id="mathResetButton"', html)
        self.assertIn('id="mathTopicMetrics"', html)
        self.assertIn('id="mathTopicHint"', html)
        self.assertIn("MAX 5,000 QUESTIONS", html)
        self.assertIn("does not update model weights", html)
        self.assertIn("function verify(topic, question, answer)", agent)
        self.assertIn("function evaluateHeldout(dataset)", agent)
        self.assertIn("id=\"mathHeldoutButton\"", html)
        self.assertIn("id=\"mathHeldoutResult\"", html)
        self.assertIn("BigInt", agent)

    def test_dashboard_keyboard_and_mobile_accessibility_hooks(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        styles = (DASHBOARD / "styles.css").read_text(encoding="utf-8")

        self.assertIn('href="#mainContent"', html)
        self.assertIn('id="mainContent" class="main-column" tabindex="-1"', html)
        self.assertRegex(
            html,
            r'class="nav-button active"[^>]*aria-current="page"',
        )
        self.assertIn('setAttribute("aria-current", "page")', javascript)
        self.assertIn('removeAttribute("aria-current")', javascript)
        self.assertIn(":focus-visible", styles)
        self.assertIn(".skip-link:focus", styles)
        self.assertIn("prefers-reduced-motion: reduce", styles)
        self.assertIn("env(safe-area-inset-top)", styles)
        self.assertIn("padding-top: env(safe-area-inset-top)", styles)
        self.assertIn("env(safe-area-inset-bottom)", styles)
        self.assertIn("env(safe-area-inset-left)", styles)
        self.assertIn("env(safe-area-inset-right)", styles)
        self.assertIn("@media (pointer: coarse)", styles)
        self.assertIn("min-height: 44px", styles)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", styles)
        self.assertIn("@media (max-width: 360px)", styles)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", styles)
        self.assertIn("flex-direction: row", styles)
        self.assertIn(".topbar-right { gap: 6px; }", styles)
        self.assertIn("padding: 0 9px", styles)
        self.assertIn("min-height: 44px", styles)
        self.assertIn(".topbar-right .icon-button { width: 44px; min-height: 44px; }", styles)
        self.assertIn("@media (max-width: 360px)", styles)
        self.assertIn("padding-left: 10px; padding-right: 10px", styles)



    def test_device_access_and_pairing_controls_are_absent_from_account_free_dashboard(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        for legacy_id in ("view-devices", "deviceRamLimitValue"):
            self.assertNotIn(legacy_id, html)
        self.assertNotIn("DEVICE PAIRING", html)
        self.assertNotIn('data-view="devices"', html)
        self.assertNotIn('$("deviceRamLimitValue")', javascript)
        self.assertIn('id="ramLimitSlider"', html)
        self.assertIn("This preference is not connected to remote training", html)
        self.assertIn("does not limit hosted-runner ram or gpu vram today", html.lower())
        self.assertNotIn("WINDOWS / MACOS / LINUX", html)
        self.assertNotIn("future local training runtime", html.lower())
        self.assertNotIn("future local runtime", html.lower())

    def test_active_public_javascript_dom_id_references_exist(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        ids = re.findall(r'\\bid="([^"]+)"', html)
        references = set(re.findall(r'\\$\\("([^"]+)"\\)', javascript))
        missing = sorted(references.difference(ids))
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        self.assertEqual(missing, [])
        self.assertEqual(duplicates, [])


    def test_browser_bundle_contains_no_backend_secret_value(self):
        for path in DASHBOARD.iterdir():
            if path.is_file():
                source = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"sb_secret_[A-Za-z0-9]{12,}", source), path.name)


    def test_public_dashboard_has_no_auth_identity_or_supabase_configuration(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        config = (DASHBOARD / "config.js").read_text(encoding="utf-8")
        self.assertNotIn('id="ownerSignInForm"', html)
        self.assertNotIn('id="ownerSignOutButton"', html)
        self.assertNotIn('id="ownerSignInDialog"', html)
        self.assertNotIn("ownerUserId", html + javascript + config)
        self.assertNotIn('src="./config.js"', html)
        self.assertNotIn("supabaseUrl", config)
        self.assertNotIn("supabasePublishableKey", config)
        self.assertNotIn("sb_publishable_", config)
        self.assertNotIn("/auth/v1/", javascript)
        self.assertNotIn("/rest/v1/", javascript)
        self.assertNotIn("/storage/v1/", javascript)
        self.assertNotIn("signUp", html + javascript)

    def test_legacy_owner_storage_is_only_cleared_and_never_restored(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        init = javascript.split("async function init()", 1)[1].split("document.addEventListener", 1)[0]
        self.assertIn("clearLegacyOwnerState();", init)
        self.assertIn('sessionStorage.removeItem("ultron_training_session")', javascript)
        self.assertIn('key.indexOf("ultron_training_cache_") === 0', javascript)
        self.assertNotIn("sessionStorage.setItem", javascript)
        self.assertNotIn("localStorage.setItem(cacheKey", javascript)
        self.assertNotIn("setAccessMode", javascript)
        self.assertNotIn("loadSavedSession", javascript)
        self.assertNotIn("verifyOwnerSession", javascript)

    def test_public_dashboard_has_no_private_data_or_checkpoint_client(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        forbidden = (
            "hasVerifiedOwnerSession", "assertOwnerAccess", "signInOwner", "signOutOwner",
            "ensureSession", "apiRequest(", "storageRequest(", "refreshData(",
            "loadCheckpointCandidates", "verifyCheckpoint(", "downloadCheckpoint(",
            "loadDataLibrary", "uploadDataFile", "downloadDataFile", "deleteDataObjects",
            "readDataLibraryForQuestions", "askUltron(", "DATA_LIBRARY_BUCKET",
            "owner_id", "access_token", "refresh_token"
        )
        for token in forbidden:
            self.assertNotIn(token, javascript)
        self.assertNotIn("setInterval(", javascript)
        self.assertNotIn('addEventListener("visibilitychange"', javascript)
        self.assertNotIn("training-control.js", (DASHBOARD / "index.html").read_text(encoding="utf-8"))

    def test_public_registry_theme_and_ram_preferences_are_preserved(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('fetch("../servers.json"', javascript)
        self.assertIn('fetch("../config.json"', javascript)
        self.assertIn('id="ramLimitSlider"', html)
        self.assertIn("ultron_training_ram_limit_gb", javascript)
        self.assertIn("ultron_training_theme", javascript)
        self.assertIn('data-view="overview"', html)
        self.assertIn('data-view="learning"', html)
        self.assertIn('data-view="math"', html)
        self.assertIn('data-view="servers"', html)
        self.assertIn('data-view="settings"', html)
        self.assertIn("function clearLegacyOwnerState()", javascript)

    def test_static_training_metrics_never_claim_live_status_or_quota_usage(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('textContent = "UNTRAINED"', javascript)
        self.assertIn('textContent = "DISABLED"', javascript)
        self.assertIn("Training is disabled; no loss history is available.", javascript)
        self.assertIn("usage not measured", javascript)
        self.assertNotIn("heartbeat", javascript.lower())
        self.assertNotIn("loss_history", javascript)

    def test_legacy_storage_bucket_remains_private_and_owner_scoped(self):
        storage_sql = (ROOT / "supabase" / "storage-setup.sql").read_text(encoding="utf-8")
        self.assertIn("public = false", storage_sql)
        self.assertIn("ultron_data_library_owner_select", storage_sql)
        self.assertIn("ultron_data_library_owner_insert", storage_sql)
        self.assertIn("ultron_data_library_owner_update", storage_sql)
        self.assertIn("ultron_data_library_owner_delete", storage_sql)
        self.assertIn("(SELECT auth.uid())::text", storage_sql)

    def test_chart_redraw_is_scheduled_and_skips_hidden_views(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("function scheduleChartDraw()", javascript)
        self.assertIn("ULTRON_RUNTIME.scheduleFrame", javascript)
        self.assertIn('if (document.hidden || state.currentView !== "overview") return;', javascript)
        self.assertIn("new ResizeObserver(scheduleChartDraw)", javascript)
        self.assertIn("context.setTransform(ratio, 0, 0, ratio, 0, 0)", javascript)
        self.assertIn("if (canvas.width !== pixelWidth) canvas.width = pixelWidth;", javascript)

    def test_private_activity_view_and_renderer_are_removed_from_public_dashboard(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('id="view-activity"', html)
        self.assertNotIn('data-view="activity"', html)
        self.assertNotIn("function renderActivity()", javascript)
        self.assertNotIn("renderActivity();", javascript)

    def test_public_overview_reports_capabilities_without_fake_training_metrics(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("ULTRON is not training", javascript)
        self.assertIn("account-free website provides the public math-learning interface", javascript)
        self.assertIn("Public browser access · training disabled", javascript)
        self.assertIn('class="connection-badge">PUBLIC</span>', html)
        for label in ("NEURAL MODEL", "MATH AGENT", "PROOF CHECKER", "TRAINING"):
            self.assertIn(label, html)
        for status in ("UNTRAINED", "AVAILABLE", "LIMITED", "DISABLED"):
            self.assertIn('textContent = "' + status + '"', javascript)
        self.assertIn("No neural model has been trained", html)
        self.assertNotIn("Read-only status", html)
        self.assertNotIn('id="autoStartToggle"', html)
        self.assertNotIn("autoStartToggle", javascript)

    def test_learning_first_view_explains_verified_improvement_cycle(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        styles = (DASHBOARD / "styles.css").read_text(encoding="utf-8")
        self.assertIn('data-view="learning"', html)
        self.assertIn('id="view-learning"', html)
        self.assertIn('aria-label="ULTRON learning cycle"', html)
        self.assertIn("Generate", html)
        self.assertIn("Verify", html)
        self.assertIn("Evaluate", html)
        self.assertIn("candidate", html.lower())
        self.assertIn('learning: ["HOW ULTRON LEARNS", "Learning system"]', javascript)
        self.assertIn(".learning-cycle", styles)
        self.assertIn("Training is not running", html)
        self.assertNotIn('id="learningStartButton"', html)
        self.assertNotIn('id="remoteStartButton"', html)

    def test_dashboard_has_no_external_ai_api_endpoint(self):
        forbidden = (
            "api.openai.com",
            "generativelanguage.googleapis.com",
            "api.anthropic.com",
            "api.cohere.ai",
        )
        for path in DASHBOARD.iterdir():
            if path.is_file():
                source = path.read_text(encoding="utf-8").lower()
                for endpoint in forbidden:
                    self.assertNotIn(endpoint, source, path.name)


class DataLibraryDeletionTests(unittest.TestCase):
    def test_readme_records_pr_96_merge_deployment_and_manual_gates(self):
        readme = (ROOT / "README.md").read_text()
        latest = readme.split("## Latest verified status", 1)[1].split("\n## ", 1)[0]
        self.assertIn("PR [#96]", latest)
        self.assertIn("397199389a1c829ff3107cff5560a2c27516fd9a", latest)
        self.assertIn("236 unit tests", latest)
        self.assertIn("Chromium and WebKit", latest)
        self.assertIn("GitHub Pages build and deployment succeeded", latest)
        self.assertIn("physical iPad/phone", latest)
        self.assertIn("owner-only **Refresh status**", latest)

    def test_ram_settings_panel_wraps_and_smoke_test_checks_geometry(self):
        css = (DASHBOARD / "styles.css").read_text()
        script = (ROOT / "tests" / "dashboard_browser_smoke.py").read_text()
        self.assertIn(".ram-panel .section-heading", css)
        self.assertIn("flex-wrap: wrap", css)
        self.assertIn(".ram-panel .small-pill", css)
        self.assertIn("white-space: normal", css)
        self.assertIn(".ram-panel .ram-value-row", css)
        self.assertIn("Settings RAM controls exceed the", script)
        self.assertIn('document.querySelector("#ramLimitSlider")', script)

    def test_dashboard_browser_smoke_runs_in_chromium_and_webkit_ci(self):
        workflow = (ROOT / ".github/workflows/dashboard-browser-smoke.yml").read_text()
        script = (ROOT / "tests/dashboard_browser_smoke.py").read_text()
        self.assertIn("playwright==1.65.1", workflow)
        self.assertIn("browser: [chromium, webkit]", workflow)
        self.assertIn("python -m playwright install --with-deps ${{ matrix.browser }}", workflow)
        self.assertIn("ULTRON_BROWSER: ${{ matrix.browser }}", workflow)
        self.assertIn("python tests/dashboard_browser_smoke.py", workflow)
        self.assertIn("VIEWPORTS = (", script)
        self.assertIn('{"chromium", "webkit"}', script)
        self.assertIn("getattr(playwright, browser_name)", script)
        self.assertIn('(320, 800)', script)
        self.assertIn('(1366, 900)', script)
        self.assertIn("getBoundingClientRect().height", script)
        self.assertIn("not external_requests", script)
        self.assertIn("page.reload(wait_until=\"networkidle\")", script)

if __name__ == "__main__":
    unittest.main()
