import tempfile
import unittest
from pathlib import Path

from platform_events import PlatformEventStore


class PlatformEventStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = PlatformEventStore(Path(self.temp.name) / "events.json")

    def test_sequences_and_cursor_are_monotonic(self):
        first = self.store.publish("failure.created", subject_id="f1", details={"category": "logic"})
        second = self.store.publish("chat.session.created", subject_id="c1")
        self.assertEqual(first["seq"], 1)
        self.assertEqual(second["seq"], 2)
        page = self.store.read(after_seq=0, limit=1)
        self.assertEqual(page["events"][0]["seq"], 1)
        next_page = self.store.read(after_seq=page["cursor"])
        self.assertEqual(next_page["events"][0]["seq"], 2)

    def test_event_filter_never_expands_empty_subscription(self):
        self.store.publish("failure.created", subject_id="f1")
        self.store.publish("chat.session.created", subject_id="c1")
        empty = self.store.read(event_types=[])
        self.assertEqual(empty["events"], [])
        filtered = self.store.read(event_types=["failure.created"])
        self.assertEqual([item["event_type"] for item in filtered["events"]], ["failure.created"])

    def test_unknown_event_type_fails_closed(self):
        with self.assertRaises(ValueError):
            self.store.publish("secret.dumped")
        with self.assertRaises(ValueError):
            self.store.read(event_types=["secret.dumped"])

    def test_event_details_are_bounded(self):
        with self.assertRaises(ValueError):
            self.store.publish("failure.created", details={"blob": "x" * 9000})


if __name__ == "__main__":
    unittest.main()
