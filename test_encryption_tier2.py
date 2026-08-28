import platform
import tempfile
import unittest
from pathlib import Path

from auth import AuthService
from backup_manager import create_portable_backup, restore_backup, verify_backup
from conversation import ConversationStore
from failure_dashboard import DASHBOARD_STATE_FILE, FailureDashboard, FailureEvent
from forge_student import StudentProgress
from mobile_access import MobileAccessStore
from portable_crypto import PORTABLE_MAGIC, PORTABLE_SCHEME, decrypt_portable, encrypt_portable
from portable_runtime import export_portable_runtime_bytes, reprotect_portable_runtime_bytes, verify_portable_runtime_bytes
from runtime_database import AT_REST_SCHEME, RuntimeDatabase
from student_progress import ProgressStore


PASSPHRASE = "Correct-Horse-Battery-Staple-2026!"


class EncryptionTier2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_portable_aesgcm_roundtrip_wrong_passphrase_and_tamper(self):
        secret = b"portable-secret-marker-9f1b"
        encrypted = encrypt_portable(secret, PASSPHRASE)
        self.assertTrue(encrypted.startswith(PORTABLE_MAGIC))
        self.assertNotIn(secret, encrypted)
        self.assertEqual(decrypt_portable(encrypted, PASSPHRASE), secret)
        with self.assertRaises(ValueError):
            decrypt_portable(encrypted, "Wrong-Portable-Passphrase-2026!")
        tampered = bytearray(encrypted)
        tampered[-1] ^= 1
        with self.assertRaises(ValueError):
            decrypt_portable(bytes(tampered), PASSPHRASE)

    def test_remaining_live_stores_can_share_one_runtime_database(self):
        database = RuntimeDatabase(self.root / "sad_runtime.sqlite3")
        auth = AuthService(database=database)
        auth.bootstrap_owner("owner", "StrongOwner123", True)
        owner = auth.login("owner", "StrongOwner123")

        conversations = ConversationStore(database=database)
        session = conversations.create_session(auth.require(owner)["account_id"])
        conversations.append_turn(
            auth.require(owner)["account_id"], session["session_id"], "private chat marker", "reply", "built_in"
        )

        progress_store = ProgressStore(database=database)
        progress_store.save(StudentProgress("student-a", xp=100))

        mobile = MobileAccessStore(database=database)
        pairing = mobile.create_pairing("phone")
        mobile.consume_pairing(pairing["code"])

        dashboard = FailureDashboard(auth, DASHBOARD_STATE_FILE, database=database)
        dashboard.ingest(FailureEvent("sad", "general", "private failure marker", [{"test": "failed"}], "review"))

        names = set(database.document_names())
        self.assertTrue({
            "accounts", "chat_history", "student_progress", "mobile_access", "dashboard_state"
        }.issubset(names))
        self.assertNotIn("StrongOwner123", (self.root / "sad_runtime.sqlite3").read_bytes().decode("latin1"))

    def test_portable_runtime_export_is_host_neutral_and_reprotects_on_windows(self):
        source = RuntimeDatabase(self.root / "source.sqlite3")
        source.write_document("sample", {"schema_version": 1, "secret": "runtime-secret-marker-31cf"})
        portable = export_portable_runtime_bytes(database=source)
        self.assertTrue(verify_portable_runtime_bytes(portable))
        self.assertIn(b"runtime-secret-marker-31cf", portable)

        if platform.system() != "Windows":
            with self.assertRaises(OSError):
                reprotect_portable_runtime_bytes(portable)
            return

        protected = reprotect_portable_runtime_bytes(portable)
        self.assertNotIn(b"runtime-secret-marker-31cf", protected)
        target = self.root / "target.sqlite3"
        target.write_bytes(protected)
        rebound = RuntimeDatabase(target, protect_at_rest=True)
        self.assertEqual(rebound.read_document("sample", {})["secret"], "runtime-secret-marker-31cf")
        status = rebound.at_rest_status()
        self.assertTrue(status["protected"])
        self.assertEqual(status["scheme"], AT_REST_SCHEME)

    def test_portable_backup_hides_payload_and_rejects_wrong_passphrase(self):
        source_root = self.root / "source"
        (source_root / "local_data").mkdir(parents=True)
        database = RuntimeDatabase(source_root / "local_data" / "sad_runtime.sqlite3")
        database.write_document("sample", {"schema_version": 1, "secret": "backup-secret-marker-4ea9"})
        (source_root / ".env").write_text("PRIVATE_ENV=backup-env-secret-712a\n", encoding="utf-8")
        destination = self.root / "portable.sadbak"

        manifest = create_portable_backup(destination, PASSPHRASE, root=source_root)
        raw = destination.read_bytes()
        self.assertEqual(manifest["container_protection"], PORTABLE_SCHEME)
        self.assertEqual(manifest["runtime_database_mode"], "portable-host-neutral")
        self.assertNotIn(b"backup-secret-marker-4ea9", raw)
        self.assertNotIn(b"backup-env-secret-712a", raw)
        self.assertTrue(verify_backup(destination, passphrase=PASSPHRASE))
        with self.assertRaises(ValueError):
            verify_backup(destination, passphrase="Wrong-Portable-Passphrase-2026!")

    @unittest.skipUnless(platform.system() == "Windows", "portable restore re-key is a Windows deployment test")
    def test_portable_restore_rebinds_runtime_to_destination_windows_user(self):
        source_root = self.root / "source"
        target_root = self.root / "target"
        (source_root / "local_data").mkdir(parents=True)
        source = RuntimeDatabase(source_root / "local_data" / "sad_runtime.sqlite3")
        source.write_document("sample", {"schema_version": 1, "secret": "cross-profile-secret-889a"})
        destination = self.root / "portable.sadbak"
        create_portable_backup(destination, PASSPHRASE, root=source_root)

        result = restore_backup(
            destination,
            root=target_root,
            explicitly_approved=True,
            passphrase=PASSPHRASE,
        )
        self.assertEqual(result["container_protection"], PORTABLE_SCHEME)
        restored_path = target_root / "local_data" / "sad_runtime.sqlite3"
        self.assertNotIn(b"cross-profile-secret-889a", restored_path.read_bytes())
        restored = RuntimeDatabase(restored_path, protect_at_rest=True)
        self.assertEqual(restored.read_document("sample", {})["secret"], "cross-profile-secret-889a")


if __name__ == "__main__":
    unittest.main()
