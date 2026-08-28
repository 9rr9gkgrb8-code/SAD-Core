import tempfile
import unittest
from pathlib import Path

from windows_doctor import check_private_data_writable, check_runtime_database, check_windows


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


if __name__ == "__main__":
    unittest.main()
