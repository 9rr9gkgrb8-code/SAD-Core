import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from api import SadApiService
from auth import AuthService
from failure_dashboard import FailureDashboard
from mobile_access import MobileAccessStore
from student_progress import ProgressStore


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 27, 22, 0, tzinfo=timezone.utc)

    def now(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class MobileAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = Clock()
        self.store = MobileAccessStore(self.root / "mobile.json", now=self.clock.now)

    def test_pairing_is_single_use_and_raw_secrets_are_not_persisted(self):
        pairing = self.store.create_pairing("Student phone", "learning")
        paired = self.store.consume_pairing(pairing["code"], "Phone 1")
        raw = (self.root / "mobile.json").read_text(encoding="utf-8")
        self.assertNotIn(pairing["code"], raw)
        self.assertNotIn(paired["device_token"], raw)
        self.assertEqual(self.store.require_device(paired["device_token"])["mode"], "learning")
        with self.assertRaises(PermissionError):
            self.store.consume_pairing(pairing["code"], "Phone 2")

    def test_pairing_expires_and_device_can_be_revoked(self):
        pairing = self.store.create_pairing("Owner phone", "full_role")
        self.clock.advance(minutes=6)
        with self.assertRaises(PermissionError):
            self.store.consume_pairing(pairing["code"])

        fresh = self.store.create_pairing("Owner phone", "full_role")
        paired = self.store.consume_pairing(fresh["code"])
        device = self.store.revoke_device(paired["device"]["device_id"])
        self.assertIsNotNone(device["revoked_at"])
        with self.assertRaises(PermissionError):
            self.store.require_device(paired["device_token"])

    def test_device_mode_is_fail_closed(self):
        with self.assertRaises(ValueError):
            self.store.create_pairing("Phone", "everything")

    def test_only_owner_management_permission_can_create_pairings(self):
        auth = AuthService(self.root / "accounts.json")
        auth.bootstrap_owner("owner", "StrongOwner123", True)
        owner = auth.login("owner", "StrongOwner123")
        auth.create_account("student", "StrongStudent123", "student", owner)
        student = auth.login("student", "StrongStudent123")
        service = SadApiService(
            auth,
            FailureDashboard(auth, self.root / "dashboard.json"),
            ProgressStore(self.root / "progress.json"),
            self.store,
        )
        headers = lambda value: {"Authorization": f"Bearer {value}"}
        _, created = service.dispatch("POST", "/v1/mobile/pairings", headers(owner), {"label": "My phone", "mode": "full_role"})
        self.assertEqual(len(created["code"]), 8)
        with self.assertRaises(PermissionError):
            service.dispatch("POST", "/v1/mobile/pairings", headers(student), {"label": "Student phone"})

    def test_state_schema_contains_only_expected_collections(self):
        self.store.create_pairing("Phone")
        data = json.loads((self.root / "mobile.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["pairings"], list)
        self.assertIsInstance(data["devices"], list)


if __name__ == "__main__":
    unittest.main()
