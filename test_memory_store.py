import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from memory_store import MemoryStore


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 28, 1, 0, tzinfo=timezone.utc)

    def now(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = Clock()
        self.store = MemoryStore(Path(self.temp.name) / "memory.json", now=self.clock.now)

    def test_memory_is_private_to_account_and_searchable(self):
        first = self.store.create("a", "project", "SAD", "Build a local-first platform")
        self.store.create("b", "note", "Private", "Different account")
        self.assertEqual([item["memory_id"] for item in self.store.list("a")], [first["memory_id"]])
        self.assertEqual(len(self.store.search("a", "local-first")), 1)
        self.assertEqual(self.store.search("a", "different account"), [])
        with self.assertRaises(KeyError):
            self.store.update("b", first["memory_id"], {"enabled": False})
        with self.assertRaises(KeyError):
            self.store.delete("b", first["memory_id"])

    def test_enabled_and_expiring_memory_controls_context(self):
        active = self.store.create("a", "preference", "Style", "Keep answers direct", enabled=True)
        disabled = self.store.create("a", "note", "Hidden", "Do not inject this", enabled=False)
        expiring = self.store.create(
            "a", "goal", "Short term", "Finish UAT",
            expires_at=(self.clock.now() + timedelta(minutes=5)).isoformat(),
        )
        context = self.store.context("a")
        self.assertTrue(any("Keep answers direct" in item for item in context))
        self.assertTrue(any("Finish UAT" in item for item in context))
        self.assertFalse(any("Do not inject this" in item for item in context))
        self.store.update("a", active["memory_id"], {"enabled": False})
        self.clock.advance(minutes=6)
        self.assertEqual(self.store.context("a"), [])
        self.assertTrue(any(item["memory_id"] == disabled["memory_id"] for item in self.store.list("a")))

    def test_validation_and_delete_are_fail_closed(self):
        with self.assertRaises(ValueError):
            self.store.create("a", "secret", "Bad", "No")
        with self.assertRaises(ValueError):
            self.store.create("a", "note", "", "No title")
        item = self.store.create("a", "fact", "Fact", "A fact")
        result = self.store.delete("a", item["memory_id"])
        self.assertTrue(result["deleted"])
        with self.assertRaises(KeyError):
            self.store.delete("a", item["memory_id"])


if __name__ == "__main__":
    unittest.main()
