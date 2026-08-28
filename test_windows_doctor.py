import platform
import tempfile
import unittest
from pathlib import Path

from windows_doctor import (
    check_dpapi,
    check_portable_backup_crypto,
    check_private_data_writable,
    check_runtime_database,
    check_runtime_protection,
    check_windows,
)


class WindowsDoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_windows_platform_gate_is_explicit(self):
        self.assertEqual(check_windows("Windows").status, "pass")
        self.assertEqual(check_windows("Linux").status, "block")

    def test_private_runtime_directory_is_writable(self):
        check = check_private_data_writable(self.root)
        self.assertEqual(check.status, "pass")
        self.assertTrue((self.root / "local_data").is_dir())

    def test_runtime_database_is_created_and_integrity_checked(self):
        check = check_runtime_database(self.root)
        self.assertEqual(check.status, "pass")
        self.assertTrue((self.root / "local_data" / "sad_runtime.sqlite3").is_file())

    def test_portable_backup_crypto_dependency_is_ready(self):
        check = check_portable_backup_crypto()
        self.assertEqual(check.status, "pass")
        self.assertIn("cryptography==50.0.1", check.detail)

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_dpapi_preflight_passes_on_windows(self):
        self.assertEqual(check_dpapi().status, "pass")

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_runtime_protection_preflight_enables_dpapi(self):
        check = check_runtime_protection(self.root)
        self.assertEqual(check.status, "pass")
        protected = Path(self.root) / "local_data" / "sad_runtime.sqlite3"
        self.assertTrue(protected.is_file())

    @unittest.skipIf(platform.system() == "Windows", "non-Windows behavior")
    def test_dpapi_checks_fail_closed_off_windows(self):
        self.assertEqual(check_dpapi().status, "block")
        self.assertEqual(check_runtime_protection(self.root).status, "block")


if __name__ == "__main__":
    unittest.main()
