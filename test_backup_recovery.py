import platform
import tempfile
import unittest
from pathlib import Path
import zipfile

from backup_manager import (
    BACKUP_DPAPI_MAGIC,
    create_backup,
    encrypt_legacy_backup,
    restore_backup,
    verify_backup,
)
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

    def test_plaintext_compatibility_backup_round_trip_is_explicit(self):
        manifest = create_backup(self.backup, root=self.root, allow_plaintext=True)
        self.assertEqual(manifest["format"], "sad-runtime-backup")
        self.assertEqual(manifest["container_protection"], "plaintext-legacy")
        with self.assertRaises(ValueError):
            verify_backup(self.backup)
        verified = verify_backup(self.backup, allow_plaintext=True)
        self.assertEqual(verified["file_count"], manifest["file_count"])
        self.assertTrue(any(item["path"] == "local_data/sad_runtime.sqlite3" for item in verified["files"]))

    def test_plaintext_restore_requires_explicit_backup_allowance_and_restore_approval(self):
        create_backup(self.backup, root=self.root, allow_plaintext=True)
        (self.root / "accounts.json").write_text("changed", encoding="utf-8")
        with self.assertRaises(PermissionError):
            restore_backup(self.backup, root=self.root, allow_plaintext=True)
        with self.assertRaises(ValueError):
            restore_backup(self.backup, root=self.root, explicitly_approved=True)
        result = restore_backup(
            self.backup, root=self.root, explicitly_approved=True, allow_plaintext=True
        )
        self.assertTrue(result["restored"])
        self.assertEqual(result["container_protection"], "plaintext-legacy")
        self.assertEqual((self.root / "accounts.json").read_text(encoding="utf-8"), '{"accounts":[]}')
        restored_db = RuntimeDatabase(self.root / "local_data" / "sad_runtime.sqlite3")
        self.assertEqual(restored_db.read_document("memory", {})["memories"]["a"]["title"], "saved")

    def test_tampered_plaintext_archive_is_rejected_before_restore(self):
        create_backup(self.backup, root=self.root, allow_plaintext=True)
        tampered = self.base / "tampered.zip"
        with zipfile.ZipFile(self.backup, "r") as source, zipfile.ZipFile(tampered, "w") as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "accounts.json":
                    data = b"tampered"
                target.writestr(item, data)
        with self.assertRaises(ValueError):
            verify_backup(tampered, allow_plaintext=True)
        with self.assertRaises(ValueError):
            restore_backup(
                tampered, root=self.root, explicitly_approved=True, allow_plaintext=True
            )

    def test_backup_rejects_destination_inside_runtime_tree(self):
        with self.assertRaises(ValueError):
            create_backup(
                self.root / "local_data" / "bad.zip", root=self.root, allow_plaintext=True
            )

    def test_plaintext_archive_with_undeclared_path_is_rejected(self):
        create_backup(self.backup, root=self.root, allow_plaintext=True)
        extra = self.base / "extra.zip"
        with zipfile.ZipFile(self.backup, "r") as source, zipfile.ZipFile(extra, "w") as target:
            for item in source.infolist():
                target.writestr(item, source.read(item.filename))
            target.writestr("../../escape.txt", "bad")
        with self.assertRaises(ValueError):
            verify_backup(extra, allow_plaintext=True)

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_windows_backup_is_dpapi_protected_and_round_trips(self):
        encrypted = self.base / "backups" / "state.sadbak"
        manifest = create_backup(encrypted, root=self.root)
        self.assertEqual(manifest["container_protection"], "windows-dpapi-user-v1")
        raw = encrypted.read_bytes()
        self.assertTrue(raw.startswith(BACKUP_DPAPI_MAGIC))
        self.assertNotIn(b'{"accounts":[]}', raw)
        self.assertFalse(zipfile.is_zipfile(encrypted))
        verified = verify_backup(encrypted)
        self.assertEqual(verified["file_count"], manifest["file_count"])

        (self.root / "accounts.json").write_text("changed", encoding="utf-8")
        result = restore_backup(encrypted, root=self.root, explicitly_approved=True)
        self.assertEqual(result["container_protection"], "windows-dpapi-user-v1")
        self.assertEqual((self.root / "accounts.json").read_text(encoding="utf-8"), '{"accounts":[]}')

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_windows_encrypted_backup_detects_ciphertext_tampering(self):
        encrypted = self.base / "backups" / "tamper.sadbak"
        create_backup(encrypted, root=self.root)
        raw = bytearray(encrypted.read_bytes())
        raw[len(raw) // 2] ^= 0x01
        encrypted.write_bytes(bytes(raw))
        with self.assertRaises(ValueError):
            verify_backup(encrypted)

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_legacy_plaintext_backup_can_be_converted_to_dpapi(self):
        legacy = self.base / "legacy.zip"
        encrypted = self.base / "legacy.sadbak"
        create_backup(legacy, root=self.root, allow_plaintext=True)
        result = encrypt_legacy_backup(legacy, encrypted)
        self.assertEqual(result["container_protection"], "windows-dpapi-user-v1")
        self.assertTrue(encrypted.read_bytes().startswith(BACKUP_DPAPI_MAGIC))
        self.assertTrue(zipfile.is_zipfile(legacy))
        with self.assertRaises(ValueError):
            verify_backup(legacy)

    @unittest.skipIf(platform.system() == "Windows", "non-Windows secure default")
    def test_non_windows_plaintext_backup_creation_requires_explicit_override(self):
        with self.assertRaises(OSError):
            create_backup(self.backup, root=self.root)


if __name__ == "__main__":
    unittest.main()
