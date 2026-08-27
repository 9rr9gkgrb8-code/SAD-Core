import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversation import ConversationStore, generate_chat_reply


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "chat_history.json"
        self.store = ConversationStore(self.path)

    def test_sessions_are_private_durable_and_archivable(self):
        created = self.store.create_session("account-a")
        session_id = created["session_id"]
        self.store.append_turn("account-a", session_id, "Tell me about conveyors", "Sure.", "built_in")

        reloaded = ConversationStore(self.path)
        saved = reloaded.get_session("account-a", session_id)
        self.assertEqual(saved["messages"][0]["text"], "Tell me about conveyors")
        self.assertEqual(saved["messages"][1]["text"], "Sure.")
        self.assertEqual(saved["title"], "Tell me about conveyors")

        with self.assertRaises(KeyError):
            reloaded.get_session("account-b", session_id)

        reloaded.archive_session("account-a", session_id)
        self.assertEqual(reloaded.list_sessions("account-a"), [])
        with self.assertRaises(KeyError):
            reloaded.get_session("account-a", session_id)

    def test_empty_and_oversized_messages_fail_closed(self):
        session = self.store.create_session("account-a")
        with self.assertRaises(ValueError):
            self.store.append_turn("account-a", session["session_id"], "", "reply", "built_in")
        with self.assertRaises(ValueError):
            self.store.append_turn("account-a", session["session_id"], "x" * 50001, "reply", "built_in")

    def test_local_model_receives_recent_history(self):
        session = {
            "messages": [
                {"role": "user", "text": "First question"},
                {"role": "assistant", "text": "First answer"},
            ]
        }
        with patch("conversation.generate_local_response", return_value="Local reply") as generate:
            reply, engine = generate_chat_reply("Follow up", {"display_name": "Ken", "level": 1}, session)
        self.assertEqual((reply, engine), ("Local reply", "local_model"))
        generate.assert_called_once_with(
            "Follow up",
            "Ken",
            [("User", "First question"), ("Sasha", "First answer")],
        )

    def test_builtin_dialogue_is_available_when_local_model_is_not(self):
        with patch("conversation.generate_local_response", return_value=None):
            reply, engine = generate_chat_reply("hello", {"display_name": "Ken", "level": 1}, {"messages": []})
        self.assertEqual(engine, "built_in")
        self.assertIn("Ken", reply)


if __name__ == "__main__":
    unittest.main()
