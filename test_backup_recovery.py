import json
import tempfile
import unittest
from pathlib import Path
import zipfile

from backup_manager import create_backup, restore_backup, verify_backup
from runtime_database import RuntimeDatabase


class BackupRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "sad"
        self.root.mkdir()
        (self.root / "accounts.json").write_text('{"accounts":[]}', encoding="utf-8")
        local_data = self.root / "local_data"
        local_data.mkdir()
        self.db = RuntimeDatabase(local_data / "sad_runtime.sqlite3")
        self.db.write_document("memory", {"schema_version": 1, "memories": {"a": {"title": "saved"}}})
        self.backup = self.base / "backups" / "state.zip"

    def test_backup_round_trip_verifies_hashes_and_sqlite(self):
        manifest = create_backup(self.backup, root=self.root)
        self.assertEqual(manifest["format"], "sad-runtime-backup")
        verified = verify_backup(self.backup)
        self.assertEqual(verified["file_count"], manifest["file_count"])
        self.assertTrue(any(item["path"] == "local_data/sad_runtime.sqlite3" for item in verified["files"]))

    def test_restore_requires_explicit_approval_and_restores_state(self):
        create_backup(self.backup, root=self.root)
        (self.root / "accounts.json").write_text("changed", encoding="utf-8")
        with self.assertRaises(PermissionError):
            restore_backup(self.backup, root=self.root)
        result = restore_backup(self.backup, root=self.root, explicitly_approved=True)
        self.assertTrue(result["restored"])
        self.assertEqual((self.root / "accounts.json").read_text(encoding="utf-8"), '{"accounts":[]}')
        restored_db = RuntimeDatabase(self.root / "local_data" / "sad_runtime.sqlite3")
        self.assertEqual(restored_db.read_document("memory", {})["memories"]["a"]["title"], "saved")

    def test_tampered_archive_is_rejected_before_restore(self):
        create_backup(self.backup, root=self.root)
        tampered = self.base / "tampered.zip"
        with zipfile.ZipFile(self.backup, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "accounts.json":
                    data = b"tampered"
                target.writestr(item, data)
        with self.assertRaises(ValueError):
            verify_backup(tampered)
        with self.assertRaises(ValueError):
            restore_backup(tampered, root=self.root, explicitly_approved=True)

    def test_backup_rejects_destination_inside_runtime_tree(self):
        with self.assertRaises(ValueError):
            create_backup(self.root / "local_data" / "bad.zip", root=self.root)

    def test_archive_with_undeclared_path_is_rejected(self):
        create_backup(self.backup, root=self.root)
        extra = self.base / "extra.zip"
        with zipfile.ZipFile(self.backup, "r") as source, zipfile.ZipFile(extra, "w") as target:
            for item in source.infolist():
                target.writestr(item, source.read(item.filename))
            target.writestr("../../escape.txt", "bad")
        with self.assertRaises(ValueError):
            verify_backup(extra)


if __name__ == "__main__":
    unittest.main()
