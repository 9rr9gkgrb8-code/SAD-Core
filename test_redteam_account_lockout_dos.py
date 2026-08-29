import tempfile
import unittest
from pathlib import Path

from auth import AuthService
from mobile_gateway import mobile_route_allowed


class RedTeamAccountLockoutDoSTests(unittest.TestCase):
    """Prove a paired learning device can intentionally lock a known account."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.auth = AuthService(Path(self.temp.name) / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)

    def test_learning_device_can_reach_login_route_and_lock_owner(self):
        # Pairing limits which routes a phone can reach, but a paired learning device is
        # explicitly allowed to call the general login endpoint for any username.
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/auth/login"))

        # Five attacker-controlled wrong attempts trigger the account lockout.
        for _ in range(5):
            self.assertIsNone(self.auth.login("owner", "AttackerWrong999"))

        # The real owner password is now rejected during the lock window.
        self.assertIsNone(self.auth.login("owner", "StrongOwner123"))


if __name__ == "__main__":
    unittest.main()
