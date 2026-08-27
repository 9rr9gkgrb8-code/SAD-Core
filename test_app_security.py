import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import app
from auth import AuthService


class AppSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.auth = AuthService(Path(self.temp.name) / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("student", "StrongStudent123", "student", owner)

    def test_student_cannot_enter_repair_workflow(self):
        student = self.auth.login("student", "StrongStudent123")
        output = io.StringIO()
        with patch("builtins.input", side_effect=["repair status", "logout"]), redirect_stdout(output):
            app.chat(0, {"level": 0, "user_name": "student"}, False, self.auth, student)
        self.assertIn("Owner authorization is required", output.getvalue())

    def test_expired_or_missing_session_cannot_enter_repair_workflow(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["approve failure", "quit"]), redirect_stdout(output):
            app.chat(0, {"level": 0, "user_name": "user"}, False, self.auth, "forged-token")
        self.assertIn("Owner authorization is required", output.getvalue())

    def test_main_entry_point_requires_and_accepts_login(self):
        output = io.StringIO()
        with patch.object(app, "AuthService", return_value=self.auth), \
             patch("builtins.input", side_effect=["owner", "logout"]), \
             patch.object(app, "getpass", return_value="StrongOwner123"), \
             redirect_stdout(output):
            app.main()
        self.assertIn("Welcome back, owner", output.getvalue())
        self.assertIn("logged out", output.getvalue())

    def test_main_entry_point_rejects_bad_login(self):
        output = io.StringIO()
        with patch.object(app, "AuthService", return_value=self.auth), \
             patch("builtins.input", return_value="owner"), \
             patch.object(app, "getpass", return_value="WrongPassword123"), \
             redirect_stdout(output):
            app.main()
        self.assertIn("Login failed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
