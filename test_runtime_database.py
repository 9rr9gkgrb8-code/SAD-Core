import json
import platform
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from runtime_database import AT_REST_SCHEME, RuntimeDatabase


class RuntimeDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = RuntimeDatabase(self.root / "runtime.sqlite3")

    def test_document_round_trip_is_transactional_and_integrity_checked(self):
        self.assertTrue(self.db.quick_check())
        self.assertEqual(self.db.read_document("memory", {"schema_version": 1}), {"schema_version": 1})
        value = {"schema_version": 1, "memories": {"x": {"title": "hello"}}}
        self.db.write_document("memory", value, max_bytes=100_000)
        self.assertEqual(self.db.read_document("memory", {}), value)
        self.assertIn("memory", self.db.document_names())
        self.assertTrue(self.db.quick_check())

    def test_legacy_json_import_is_validated_verified_and_archived(self):
        source = self.root / "memory.json"
        source.write_text(json.dumps({"schema_version": 1, "memories": {}}), encoding="utf-8")

        def validate(value):
            if value.get("schema_version") != 1 or not isinstance(value.get("memories"), dict):
                raise ValueError("bad memory")

        import runtime_database
        old_archive = runtime_database.LEGACY_IMPORT_DIRECTORY
        runtime_database.LEGACY_IMPORT_DIRECTORY = self.root / "legacy_imported"
        self.addCleanup(setattr, runtime_database, "LEGACY_IMPORT_DIRECTORY", old_archive)

        self.assertTrue(self.db.import_json_document("memory", source, validate, max_bytes=100_000))
        self.assertFalse(source.exists())
        self.assertTrue((self.root / "legacy_imported" / "memory.json.imported").is_file())
        self.assertEqual(self.db.read_document("memory", {})["schema_version"], 1)

    def test_conflicting_live_json_and_sqlite_state_fail_closed(self):
        self.db.write_document("memory", {"schema_version": 1, "memories": {}}, max_bytes=100_000)
        source = self.root / "memory.json"
        source.write_text(json.dumps({"schema_version": 1, "memories": {}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.db.import_json_document("memory", source, lambda value: None, max_bytes=100_000)

    def test_snapshot_is_standalone_and_verified(self):
        self.db.write_document("tool_actions", {"schema_version": 1, "actions": {}}, max_bytes=100_000)
        snapshot = self.root / "snapshot.sqlite3"
        self.db.snapshot(snapshot)
        self.assertTrue(RuntimeDatabase.verify_snapshot(snapshot))
        copy = RuntimeDatabase(snapshot)
        self.assertEqual(copy.read_document("tool_actions", {})["schema_version"], 1)

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_protected_database_hides_plaintext_and_round_trips(self):
        path = self.root / "protected.sqlite3"
        protected = RuntimeDatabase(path, protect_at_rest=True)
        secret = "SAD-very-private-memory-value"
        value = {"schema_version": 1, "memories": {"x": {"title": secret}}}
        protected.write_document("memory", value, max_bytes=100_000)
        self.assertEqual(protected.read_document("memory", {}), value)
        self.assertEqual(protected.at_rest_status()["scheme"], AT_REST_SCHEME)

        raw = path.read_bytes()
        self.assertNotIn(secret.encode("utf-8"), raw)
        with closing(sqlite3.connect(str(path))) as connection:
            payload = connection.execute(
                "SELECT payload_json FROM runtime_documents WHERE namespace='memory'"
            ).fetchone()[0]
        self.assertNotIn(secret, payload)
        envelope = json.loads(payload)
        self.assertEqual(envelope["scheme"], AT_REST_SCHEME)
        self.assertNotIn(secret, envelope["blob"])

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_plaintext_database_migrates_transactionally_to_dpapi(self):
        path = self.root / "migrate.sqlite3"
        plain = RuntimeDatabase(path, protect_at_rest=False)
        secret = "legacy-plaintext-secret"
        value = {"schema_version": 1, "memories": {"x": {"title": secret}}}
        plain.write_document("memory", value, max_bytes=100_000)
        self.assertIn(secret.encode("utf-8"), path.read_bytes())

        protected = RuntimeDatabase(path, protect_at_rest=True)
        self.assertEqual(protected.read_document("memory", {}), value)
        self.assertTrue(protected.at_rest_status()["protected"])
        self.assertNotIn(secret.encode("utf-8"), path.read_bytes())

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_protected_database_rejects_plaintext_downgrade(self):
        path = self.root / "downgrade.sqlite3"
        protected = RuntimeDatabase(path, protect_at_rest=True)
        protected.write_document("memory", {"schema_version": 1, "memories": {}}, max_bytes=100_000)
        with closing(sqlite3.connect(str(path))) as connection:
            connection.execute(
                "UPDATE runtime_documents SET payload_json=? WHERE namespace='memory'",
                (json.dumps({"schema_version": 1, "memories": {"leak": "plaintext"}}),),
            )
            connection.commit()
        with self.assertRaises(ValueError):
            RuntimeDatabase(path, protect_at_rest=True)


if __name__ == "__main__":
    unittest.main()
