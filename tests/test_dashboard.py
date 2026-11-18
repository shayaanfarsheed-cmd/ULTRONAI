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
        self.assertIn("state.publicMode = !isOwner", javascript)
        self.assertIn('ownerUserId: ""', config)
        self.assertNotIn("signup", javascript.lower())
        self.assertNotIn("signUp", html)

    def test_guest_mode_is_default_and_owner_session_is_verified(self):
        javascript = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        self.assertIn("publicMode: true", javascript)
        self.assertIn('AUTH_ROOT + "user"', javascript)
        self.assertIn("setAccessMode(restoredOwner)", javascript)
        self.assertIn('$("ownerPassword").value = ""', javascript)

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
