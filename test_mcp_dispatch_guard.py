import unittest
import tempfile
from pathlib import Path

from mcp_dispatch_guard import (
    GovernedMCPDispatcher, MCPGrant, SQLiteOperationReservations, MCPAuthorizationError,
    MCPDuplicateOperationError, argument_digest,
)


class MCPDispatchGateTests(unittest.TestCase):
    def setUp(self):
        self.active = True
        self.reserved = set()
        self.effects = 0

        def reserve(key):
            if key in self.reserved:
                return False
            self.reserved.add(key)
            return True

        self.dispatcher = GovernedMCPDispatcher(lambda grant: self.active, reserve)
        self.args = {"path": "sandbox/a"}
        self.grant = MCPGrant("owner", "repair", argument_digest(self.args), "approval-1", True)

    def execute(self):
        self.effects += 1
        return "done"

    def call(self, grant=None, principal="owner", args=None):
        return self.dispatcher.call(
            principal=principal, tool="repair",
            arguments=self.args if args is None else args,
            grant=self.grant if grant is None else grant,
            execute=self.execute,
        )

    def test_valid_approved_operation_runs_once(self):
        self.assertEqual(self.call(), "done")
        self.assertEqual(self.effects, 1)

    def test_direct_call_without_approval_is_rejected(self):
        with self.assertRaises(MCPAuthorizationError):
            self.dispatcher.call(principal="owner", tool="repair", arguments=self.args,
                                 grant=None, execute=self.execute)
        self.assertEqual(self.effects, 0)

    def test_cross_principal_rejected(self):
        with self.assertRaises(MCPAuthorizationError):
            self.call(principal="other")
        self.assertEqual(self.effects, 0)

    def test_changed_arguments_rejected(self):
        with self.assertRaises(MCPAuthorizationError):
            self.call(args={"path": "outside"})
        self.assertEqual(self.effects, 0)

    def test_revoked_approval_rejected(self):
        self.active = False
        with self.assertRaises(MCPAuthorizationError):
            self.call()
        self.assertEqual(self.effects, 0)

    def test_retry_cannot_repeat_side_effect(self):
        self.call()
        with self.assertRaises(MCPDuplicateOperationError):
            self.call()
        self.assertEqual(self.effects, 1)

    def test_reservation_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.sqlite3"
            first = SQLiteOperationReservations(path)
            self.assertTrue(first("key-1"))
            second = SQLiteOperationReservations(path)
            self.assertFalse(second("key-1"))
            self.assertTrue(second("key-2"))

    def test_unapproved_grant_rejected(self):
        grant = MCPGrant("owner", "repair", argument_digest(self.args), "approval-1", False)
        with self.assertRaises(MCPAuthorizationError):
            self.call(grant=grant)


if __name__ == "__main__":
    unittest.main()
