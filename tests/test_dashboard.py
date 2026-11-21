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
        self.assertIn("does not cap the memory available to a hosted runner", html)
        self.assertNotIn("WINDOWS / MACOS / LINUX", html)
        self.assertNotIn("future local training runtime", html.lower())
        self.assertNotIn("future local runtime", html.lower())

    def test_all_static_javascript_id_references_exist(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        ids = re.findall(r'\bid="([^"]+)"', html)
        references = set(re.findall(r'\$\("([^"]+)"\)', javascript))
        # These IDs belong only to unreachable legacy owner-auth helpers. The public
        # dashboard intentionally has no corresponding sign-in or sign-out UI.
        legacy_auth_ids = {
            "ownerSignInButton", "ownerSignOutButton", "ownerSignInDialog",
            "ownerSignInForm", "ownerCancelButton", "ownerSubmitButton",
            "ownerAuthMessage", "ownerEmail", "ownerPassword",
        }
        missing = sorted(references.difference(ids).difference(legacy_auth_ids))
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        self.assertEqual(missing, [])
        self.assertEqual(duplicates, [])

    def test_browser_bundle_contains_no_backend_secret_value(self):
        for path in DASHBOARD.iterdir():
            if path.is_file():
                source = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"sb_secret_[A-Za-z0-9]{12,}", source), path.name)

    def test_public_dashboard_has_no_sign_in_or_published_owner_identifier(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        config = (DASHBOARD / "config.js").read_text(encoding="utf-8")
        self.assertNotIn('id="ownerSignInForm"', html)
        self.assertNotIn('id="ownerSignOutButton"', html)
        self.assertNotIn('id="ownerSignInDialog"', html)
        self.assertNotIn("ownerUserId", config)
        self.assertIn("state.publicMode = nextPublicMode", javascript)
        self.assertRegex(config, r'supabasePublishableKey: "sb_publishable_[A-Za-z0-9_-]+"')
        self.assertNotIn("REPLACE_WITH", config)
        self.assertNotIn("signUp", html)

    def test_public_mode_is_default_and_legacy_sessions_are_cleared(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        init = javascript.split("async function init()", 1)[1].split("document.addEventListener", 1)[0]
        self.assertIn("publicMode: true", javascript)
        self.assertIn("clearLegacyOwnerState();", init)
        self.assertIn("setAccessMode(false);", init)
        self.assertNotIn("loadSavedSession()", init)
        self.assertNotIn("verifyOwnerSession()", init)
        self.assertIn("sessionStorage.removeItem(SESSION_KEY)", javascript)
        self.assertIn("key.indexOf(CACHE_PREFIX) === 0", javascript)

    def test_session_refresh_is_single_flight_and_invalidated_on_auth_transition(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("let sessionRefreshPromise = null;", javascript)
        self.assertIn("if (sessionRefreshPromise) return sessionRefreshPromise;", javascript)
        self.assertIn("if (sessionRefreshPromise === refreshPromise) sessionRefreshPromise = null;", javascript)
        access_mode = javascript.split("function setAccessMode(isOwner)", 1)[1].split("async function verifyOwnerSession", 1)[0]
        self.assertIn("sessionRefreshPromise = null;", access_mode)
        refresh = javascript.split("async function ensureSession()", 1)[1].split("async function apiRequest", 1)[0]
        self.assertIn("generation !== state.authGeneration", refresh)
        self.assertIn("state.session.refresh_token !== refreshToken", refresh)

    def test_private_api_and_storage_require_verified_owner_mode(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("function hasVerifiedOwnerSession()", javascript)
        self.assertIn("function assertOwnerAccess(session)", javascript)
        self.assertGreaterEqual(javascript.count("assertOwnerAccess(session);"), 2)
        self.assertIn("if (!hasVerifiedOwnerSession() || state.refreshing) return;", javascript)
        self.assertIn("if (!hasVerifiedOwnerSession() || !state.status || !state.status.run_id)", javascript)

    def test_guest_transition_clears_private_state_and_invalidates_inflight_refresh(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("state.authGeneration += 1", javascript)
        self.assertIn("state.status = null;", javascript)
        self.assertIn("state.checkpoints = [];", javascript)
        self.assertIn("generation !== state.authGeneration", javascript)
        self.assertIn("localStorage.removeItem(CACHE_PREFIX + previousUserId)", javascript)

    def test_expired_or_revoked_owner_session_returns_to_guest_mode(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("function expireOwnerSession()", javascript)
        self.assertIn("expireOwnerSession();", javascript)
        self.assertIn('if (response.status === 401) expireOwnerSession();', javascript)
        self.assertIn("Your owner session expired. Please sign in again.", javascript)

    def test_signin_clears_password_and_signout_is_local_first(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('const password = passwordInput.value;\n    passwordInput.value = "";', javascript)
        self.assertIn('passwordInput.value = "";\n      submit.disabled = false;', javascript)
        signout = javascript.split("async function signOutOwner()", 1)[1].split("function sessionFromResponse", 1)[0]
        self.assertLess(signout.index("saveSession(null);"), signout.index('fetch(AUTH_ROOT + "logout"'))

    def test_chart_redraw_is_scheduled_and_skips_hidden_views(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("function scheduleChartDraw()", javascript)
        self.assertIn("ULTRON_RUNTIME.scheduleFrame", javascript)
        self.assertIn('if (document.hidden || state.currentView !== "overview") return;', javascript)
        self.assertIn("new ResizeObserver(scheduleChartDraw)", javascript)
        self.assertIn("context.setTransform(ratio, 0, 0, ratio, 0, 0)", javascript)
        self.assertIn("if (canvas.width !== pixelWidth) canvas.width = pixelWidth;", javascript)

    def test_checkpoint_metadata_reads_are_bounded_and_auth_generation_checked(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('id="view-checkpoints"', html)
        self.assertNotIn('data-view="checkpoints"', html)
        self.assertIn("async function mapWithConcurrency(items, limit, mapper)", (DASHBOARD / "runtime.js").read_text(encoding="utf-8"))
        self.assertIn("ULTRON_RUNTIME.mapWithConcurrency(ids, 3", javascript)
        loader = javascript.split("async function loadCheckpointCandidates()", 1)[1].split("async function verifyCheckpoint", 1)[0]
        self.assertIn('Promise.all([', loader)
        self.assertIn("generation !== state.authGeneration", loader)
        self.assertIn("state.status.run_id !== runId", loader)
        self.assertIn("results.filter(Boolean)", loader)
        self.assertLess(loader.index("const listed = await storageRequest"), loader.index("state.status.run_id !== runId"))

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


    def test_owner_data_library_is_private_and_cross_browser_cloud_backed(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        storage_sql = (ROOT / "supabase" / "storage-setup.sql").read_text(encoding="utf-8")
        self.assertNotIn('data-view="data"', html)
        self.assertNotIn('id="view-data"', html)
        self.assertNotIn('id="dataUploadForm"', html)
        self.assertNotIn('id="dataFileList"', html)
        self.assertIn('const DATA_LIBRARY_BUCKET = "data-library"', javascript)
        self.assertIn('async function loadDataLibrary()', javascript)
        self.assertIn('async function uploadDataFile()', javascript)
        self.assertIn('async function downloadDataFile(name)', javascript)
        self.assertIn('async function deleteDataFile(name)', javascript)
        self.assertIn('if (!hasVerifiedOwnerSession())', javascript)
        self.assertIn('window.setInterval(function ()', javascript)
        self.assertIn('object/list/" + DATA_LIBRARY_BUCKET', javascript)
        self.assertIn("ultron_data_library_owner_select", storage_sql)
        self.assertIn("ultron_data_library_owner_insert", storage_sql)
        self.assertIn("ultron_data_library_owner_update", storage_sql)
        self.assertIn("ultron_data_library_owner_delete", storage_sql)
        self.assertIn("(SELECT auth.uid())::text", storage_sql)
        self.assertIn("public = false", storage_sql)
        self.assertIn("20971520", storage_sql)
        self.assertNotIn("service_role", javascript)

    def test_data_library_never_executes_uploaded_content(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('new Blob([bytes], {type: "application/octet-stream"})', javascript)
        self.assertIn("ULTRON will not execute uploaded files", (DASHBOARD / "index.html").read_text(encoding="utf-8"))
        self.assertIn("DATA_LIBRARY_MAX_BYTES = 20 * 1024 * 1024", javascript)
        self.assertIn("if (binary) return response.arrayBuffer();", javascript)
        api_request = javascript.split("async function apiRequest", 1)[1].split("async function storageRequest", 1)[0]
        self.assertNotIn("binary", api_request)


    def test_ask_ultron_searches_owner_data_and_shows_source_evidence(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('data-view="ask"', html)
        self.assertNotIn('id="view-ask"', html)
        self.assertNotIn('id="askQuestionForm"', html)
        self.assertNotIn('id="askResults"', html)
        self.assertIn('async function readDataLibraryForQuestions()', javascript)
        self.assertIn('async function askUltron(question)', javascript)
        self.assertIn('if (!hasVerifiedOwnerSession()) throw new Error("Sign in to the verified owner account', javascript)
        self.assertIn('object/authenticated/', javascript)
        self.assertIn('function rankAskPassages(question, passages)', javascript)
        self.assertIn('source.textContent = match.fileName', javascript)
        self.assertIn('TextDecoder("utf-8", {fatal: true})', javascript)
        self.assertIn('ASK_MAX_TOTAL_BYTES = 15 * 1024 * 1024', javascript)
        self.assertIn('ASK_MAX_FILE_BYTES = 5 * 1024 * 1024', javascript)
        self.assertIn('does not call an external AI API', html)
        self.assertNotIn('eval(', javascript)
        self.assertNotIn('new Function(', javascript)

    def test_ask_ultron_supports_only_explicit_text_formats(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('".txt", ".md", ".csv", ".json", ".lean", ".toml"', javascript)
        self.assertIn('if (!ASK_TEXT_EXTENSIONS.some', javascript)
        self.assertIn('quoted evidence, not a generated answer', javascript)

    def test_data_library_supports_owner_only_folder_upload_and_nested_paths(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="dataFolderInput" type="file" webkitdirectory directory multiple', html)
        self.assertIn("async function walkFolder(prefix, depth)", javascript)
        self.assertIn("DATA_LIBRARY_MAX_FILES = 50000", javascript)
        self.assertIn("DATA_LIBRARY_BATCH_FILES = 500", javascript)
        self.assertIn("batchCount = Math.ceil(selected.length / DATA_LIBRARY_BATCH_FILES)", javascript)
        self.assertIn("at most 50,000 files", javascript)
        self.assertIn("offset: offset", javascript)
        self.assertIn("function safeDataRelativePath(value)", javascript)
        self.assertIn("safeDataRelativePath(file.name)", javascript)
        self.assertIn("function dataObjectPath(relativePath)", javascript)
        self.assertIn("file.webkitRelativePath || file.name", javascript)
        self.assertIn("const pageSize = 500", javascript)
        self.assertIn("5000 * 1024 * 1024", javascript)
        self.assertIn("up to 50,000 files per selection", html)
        self.assertIn("batches of 500 files", html)
        self.assertIn("5,000 MiB (5 GiB)", javascript)
        self.assertIn("dataObjectPath(entry.path)", javascript)
        self.assertIn("if (!hasVerifiedOwnerSession()) throw new Error(\"Sign in to the verified owner account before uploading.\")", javascript)



class DataLibraryDeletionTests(unittest.TestCase):
    def test_data_library_supports_confirmed_owner_only_bulk_and_folder_deletion(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="dataSelectAll"', html)
        self.assertIn('id="dataDeleteSelectedButton"', html)
        self.assertIn('data-data-select=', javascript)
        self.assertIn('async function deleteDataObjects(relativePaths, confirmationMessage)', javascript)
        self.assertIn('async function deleteDataFolder(folder)', javascript)
        self.assertIn('async function deleteSelectedDataFiles()', javascript)
        self.assertIn('objectPaths.slice(offset, offset + 1000)', javascript)
        self.assertIn('if (!hasVerifiedOwnerSession()) throw new Error("Owner sign-in is required.")', javascript)
        self.assertIn('if (!window.confirm(confirmationMessage)) return;', javascript)
        self.assertIn('data-data-delete-folder=', javascript)
        self.assertIn('prefixes: objectPaths.slice(offset, offset + 1000)', javascript)

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
