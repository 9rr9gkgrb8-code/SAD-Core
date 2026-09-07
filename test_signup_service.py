import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from auth import AuthService
from signup_invites import SignupInviteStore
from signup_service import SignupSadApiService


class SignupServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.auth = AuthService(accounts_file=root / "accounts.json")
        self.auth.bootstrap_owner("owner", "OwnerPassword123", explicitly_approved=True)
        self.invites = SignupInviteStore(path=root / "invites.json")
        self.service = SignupSadApiService(auth=self.auth, signup_invites=self.invites)
        self.owner_token = self.auth.login("owner", "OwnerPassword123")

    def tearDown(self):
        self.temp.cleanup()

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_owner_invite_creates_student_and_logs_in(self):
        status, invite = self.service.dispatch("POST", "/v1/signup/invites", self.headers(self.owner_token), {
            "expires_minutes": 60, "max_uses": 1, "guardian_required": True,
        })
        self.assertEqual(status, 201)
        status, result = self.service.dispatch("POST", "/v1/signup", {}, {
            "invite_code": invite["code"], "username": "learner1", "password": "StudentPass123",
            "guardian_consent": True,
        })
        self.assertEqual(status, 201)
        self.assertEqual(result["account"]["role"], "student")
        self.assertEqual(self.auth.require(result["token"])["username"], "learner1")

    def test_signup_cannot_choose_privileged_role(self):
        _, invite = self.service.dispatch("POST", "/v1/signup/invites", self.headers(self.owner_token), {"expires_minutes": 60})
        _, result = self.service.dispatch("POST", "/v1/signup", {}, {
            "invite_code": invite["code"], "username": "learner2", "password": "StudentPass123",
            "guardian_consent": True, "role": "owner",
        })
        self.assertEqual(result["account"]["role"], "student")

    def test_invite_is_single_use(self):
        _, invite = self.service.dispatch("POST", "/v1/signup/invites", self.headers(self.owner_token), {"expires_minutes": 60})
        self.service.dispatch("POST", "/v1/signup", {}, {"invite_code": invite["code"], "username": "learner3", "password": "StudentPass123", "guardian_consent": True})
        with self.assertRaises(PermissionError):
            self.service.dispatch("POST", "/v1/signup", {}, {"invite_code": invite["code"], "username": "learner4", "password": "StudentPass123", "guardian_consent": True})

    def test_guardian_confirmation_required_by_default(self):
        _, invite = self.service.dispatch("POST", "/v1/signup/invites", self.headers(self.owner_token), {"expires_minutes": 60})
        with self.assertRaises(PermissionError):
            self.service.dispatch("POST", "/v1/signup", {}, {"invite_code": invite["code"], "username": "learner5", "password": "StudentPass123"})


if __name__ == "__main__":
    unittest.main()
