import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from auth import AuthService


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 27, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = Clock()
        self.path = Path(self.temp.name) / "accounts.json"
        self.auth = AuthService(self.path, self.clock)

    def owner_token(self):
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        return self.auth.login("owner", "StrongOwner123")

    def test_owner_bootstrap_requires_approval_and_happens_once(self):
        with self.assertRaises(PermissionError):
            self.auth.bootstrap_owner("owner", "StrongOwner123")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        with self.assertRaises(PermissionError):
            self.auth.bootstrap_owner("other", "StrongOwner456", True)

    def test_passwords_are_salted_and_never_stored_plaintext(self):
        self.owner_token()
        stored = self.path.read_text(encoding="utf-8")
        self.assertNotIn("StrongOwner123", stored)
        account = json.loads(stored)["accounts"][0]
        self.assertTrue(account["password_salt"])
        self.assertTrue(account["password_hash"])

    def test_owner_can_create_all_future_roles(self):
        token = self.owner_token()
        for username, role in (("student", "student"), ("teacher", "teacher"), ("developer", "developer"), ("reviewer", "reviewer"), ("viewer", "viewer")):
            created = self.auth.create_account(username, f"Strong{role}123", role, token)
            self.assertEqual(created["role"], role)

    def test_teacher_can_create_student_but_not_developer(self):
        owner = self.owner_token()
        self.auth.create_account("teacher", "StrongTeacher123", "teacher", owner)
        teacher = self.auth.login("teacher", "StrongTeacher123")
        self.assertEqual(self.auth.create_account("student", "StrongStudent123", "student", teacher)["role"], "student")
        with self.assertRaises(PermissionError):
            self.auth.create_account("developer", "StrongDeveloper123", "developer", teacher)

    def test_session_expires_and_logout_revokes_it(self):
        token = self.owner_token()
        self.assertEqual(self.auth.require(token)["role"], "owner")
        self.assertTrue(self.auth.logout(token))
        with self.assertRaises(PermissionError):
            self.auth.require(token)
        token = self.auth.login("owner", "StrongOwner123")
        self.clock.value += timedelta(hours=13)
        with self.assertRaises(PermissionError):
            self.auth.require(token)

    def test_repeated_bad_passwords_lock_account_temporarily(self):
        self.owner_token()
        for _ in range(5):
            self.assertIsNone(self.auth.login("owner", "WrongPassword123"))
        self.assertIsNone(self.auth.login("owner", "StrongOwner123"))
        self.clock.value += timedelta(minutes=16)
        self.assertIsNotNone(self.auth.login("owner", "StrongOwner123"))

    def test_role_permission_is_enforced(self):
        owner = self.owner_token()
        self.auth.create_account("student", "StrongStudent123", "student", owner)
        student = self.auth.login("student", "StrongStudent123")
        self.auth.require(student, "forge:play")
        with self.assertRaises(PermissionError):
            self.auth.require(student, "development:view")

    def test_profiles_are_isolated_per_account(self):
        owner = self.owner_token()
        self.auth.create_account("student", "StrongStudent123", "student", owner)
        student = self.auth.login("student", "StrongStudent123")
        self.auth.update_profile(owner, display_name="Owner Name", level=2)
        self.auth.update_profile(student, display_name="Student Name", level=1)
        self.assertEqual(self.auth.get_profile(owner), {"display_name": "Owner Name", "level": 2})
        self.assertEqual(self.auth.get_profile(student), {"display_name": "Student Name", "level": 1})

    def test_unbounded_password_input_is_rejected(self):
        with self.assertRaises(ValueError):
            self.auth.bootstrap_owner("owner", "A1" + "x" * 2000, True)


if __name__ == "__main__":
    unittest.main()
