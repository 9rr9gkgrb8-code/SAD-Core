import unittest
from types import SimpleNamespace
from mcp_tool_security import ToolAdmission, ToolUnavailable, RetryLedger, ReplayConflict

class McpToolSecurityTests(unittest.TestCase):
    def setUp(self):
        self.admission = ToolAdmission({
            "private": SimpleNamespace(permission="owner"),
            "public": SimpleNamespace(permission=None),
        })

    def test_hidden_tool_does_not_reveal_argument_schema(self):
        for tool in ("private", "missing"):
            with self.assertRaisesRegex(ToolUnavailable, "^Tool unavailable\\.$"):
                self.admission.admit(tool, "invalid shape", set(), "request-1")
        self.assertEqual([x.permission for x in self.admission.catalog(set())], [None])

    def test_authorized_tool_validates_arguments(self):
        with self.assertRaises(ValueError):
            self.admission.admit("private", [], {"owner"}, "request-1")

    def test_replay_returns_result_without_second_execution(self):
        admission = self.admission.admit("public", {"x": 1}, set(), "request-1")
        ledger = RetryLedger()
        calls = []
        def execute():
            calls.append(1)
            return {"ok": True}
        self.assertEqual(ledger.run_once(account_id="a", admission=admission, approval_id="approval-1", execute=execute), {"ok": True})
        self.assertEqual(ledger.run_once(account_id="a", admission=admission, approval_id="approval-1", execute=execute), {"ok": True})
        self.assertEqual(len(calls), 1)
        with self.assertRaises(ReplayConflict):
            ledger.run_once(account_id="a", admission=admission, approval_id="approval-2", execute=execute)

    def test_failed_execution_does_not_retry_uncertain_effect(self):
        admission = self.admission.admit("public", {}, set(), "request-2")
        ledger = RetryLedger()
        def failed():
            raise RuntimeError("uncertain effect")
        with self.assertRaises(RuntimeError):
            ledger.run_once(account_id="a", admission=admission, approval_id=None, execute=failed)
        with self.assertRaises(ReplayConflict):
            ledger.run_once(account_id="a", admission=admission, approval_id=None, execute=lambda: None)

if __name__ == "__main__":
    unittest.main()
