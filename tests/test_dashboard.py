import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


class DashboardStaticTests(unittest.TestCase):
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
        self.assertIn('ownerUserId: ""', config)
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
        self.assertIn("window.requestAnimationFrame", javascript)
        self.assertIn('if (document.hidden || state.currentView !== "overview") return;', javascript)
        self.assertIn("new ResizeObserver(scheduleChartDraw)", javascript)
        self.assertIn("context.setTransform(ratio, 0, 0, ratio, 0, 0)", javascript)
        self.assertIn("if (canvas.width !== pixelWidth) canvas.width = pixelWidth;", javascript)

    def test_checkpoint_metadata_reads_are_bounded_and_auth_generation_checked(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("async function mapWithConcurrency(items, limit, mapper)", javascript)
        self.assertIn("mapWithConcurrency(ids, 3", javascript)
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
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("Welcome to the ULTRON guest dashboard", javascript)
        self.assertIn("Private training status, history, checkpoints and device controls are not loaded", javascript)
        self.assertIn('$("autoStartToggle").disabled = true;', javascript)

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
