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

    def test_all_static_javascript_id_references_exist(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        ids = re.findall(r'\bid="([^"]+)"', html)
        references = set(re.findall(r'\$\("([^"]+)"\)', javascript))
        missing = sorted(references.difference(ids))
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        self.assertEqual(missing, [])
        self.assertEqual(duplicates, [])

    def test_browser_bundle_contains_no_backend_secret_value(self):
        for path in DASHBOARD.iterdir():
            if path.is_file():
                source = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"sb_secret_[A-Za-z0-9]{12,}", source), path.name)

    def test_owner_auth_is_allowlisted_and_has_no_signup_flow(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        config = (DASHBOARD / "config.js").read_text(encoding="utf-8")
        self.assertIn('id="ownerSignInForm"', html)
        self.assertIn('id="ownerSignOutButton"', html)
        self.assertIn("user.id !== OWNER_USER_ID", javascript)
        self.assertIn("state.publicMode = nextPublicMode", javascript)
        self.assertRegex(
            config,
            r'ownerUserId: "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"',
        )
        self.assertRegex(config, r'supabasePublishableKey: "sb_publishable_[A-Za-z0-9_-]+"')
        self.assertNotIn("REPLACE_WITH", config)
        self.assertNotIn("signup", javascript.lower())
        self.assertNotIn("signUp", html)

    def test_guest_mode_is_default_and_owner_session_is_verified(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("publicMode: true", javascript)
        self.assertIn('AUTH_ROOT + "user"', javascript)
        self.assertIn("setAccessMode(restoredOwner)", javascript)
        self.assertIn('$("ownerPassword").value = ""', javascript)

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
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("async function mapWithConcurrency(items, limit, mapper)", (DASHBOARD / "runtime.js").read_text(encoding="utf-8"))
        self.assertIn("ULTRON_RUNTIME.mapWithConcurrency(ids, 3", javascript)
        loader = javascript.split("async function loadCheckpointCandidates()", 1)[1].split("async function verifyCheckpoint", 1)[0]
        self.assertIn('Promise.all([', loader)
        self.assertIn("generation !== state.authGeneration", loader)
        self.assertIn("state.status.run_id !== runId", loader)
        self.assertIn("results.filter(Boolean)", loader)
        self.assertLess(loader.index("const listed = await storageRequest"), loader.index("state.status.run_id !== runId"))

    def test_private_activity_view_is_guest_gated(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-view="activity"', html)
        self.assertIn('id="view-activity"', html)
        self.assertIn('id="activityLogs"', html)
        self.assertIn('id="activitySwitches"', html)
        self.assertIn("function renderActivity()", javascript)
        self.assertIn("if (state.publicMode || !hasVerifiedOwnerSession())", javascript)
        self.assertIn("renderActivity();", javascript)

    def test_guest_overview_does_not_recommend_starting_training(self):
        html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("Welcome to the ULTRON guest dashboard", javascript)
        self.assertIn("Private training status, history, checkpoints and device controls are not loaded", javascript)
        self.assertIn("Training remains disabled", javascript)
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


if __name__ == "__main__":
    unittest.main()
