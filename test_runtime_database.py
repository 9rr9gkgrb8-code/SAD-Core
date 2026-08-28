import json
import tempfile
import unittest
from pathlib import Path

from runtime_database import RuntimeDatabase


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

        # Redirect the module-level archive directory by placing the DB/source under the
        # repository-independent temp root is not supported, so import itself is tested
        # with a source in a temporary local_data-shaped directory.
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


if __name__ == "__main__":
    unittest.main()
