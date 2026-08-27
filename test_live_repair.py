import json
import tempfile
import unittest
import uuid
from pathlib import Path

import live_apply
import sandbox
from auth import AuthService
from failure_dashboard import FailureDashboard, FailureEvent
from repair_planner import RepairPlanningError, plan_repair
from sad_forge_contract import Artifact, ForgeResult


class RepairPlannerTests(unittest.TestCase):
    def test_planner_accepts_one_exact_json_replacement(self):
        source = "VALUE = 1\nOTHER = 2\n"
        plan = plan_repair(
            "app.py", "Set VALUE to 2", source,
            generator=lambda prompt: json.dumps({
                "find_text": "VALUE = 1",
                "replacement_text": "VALUE = 2",
                "rationale": "Correct the configured value.",
            }),
        )
        self.assertEqual(plan["replacement_text"], "VALUE = 2")

    def test_planner_rejects_ambiguous_or_non_json_output(self):
        source = "VALUE = 1\nVALUE = 1\n"
        with self.assertRaises(RepairPlanningError):
            plan_repair(
                "app.py", "change value", source,
                generator=lambda prompt: json.dumps({"find_text": "VALUE = 1", "replacement_text": "VALUE = 2"}),
            )
        with self.assertRaises(RepairPlanningError):
            plan_repair("app.py", "change value", "VALUE = 1\n", generator=lambda prompt: "```json\n{}\n```")


class LiveRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.sandbox_root = self.project / ".sad_sandbox"
        (self.project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

        self.old_sandbox_project = sandbox.PROJECT_DIRECTORY
        self.old_sandbox_root = sandbox.SANDBOX_DIRECTORY
        self.old_apply_project = live_apply.PROJECT_DIRECTORY
        self.old_apply_root = live_apply.SANDBOX_DIRECTORY
        sandbox.PROJECT_DIRECTORY = self.project
        sandbox.SANDBOX_DIRECTORY = self.sandbox_root
        live_apply.PROJECT_DIRECTORY = self.project
        live_apply.SANDBOX_DIRECTORY = self.sandbox_root
        self.addCleanup(self._restore_globals)

    def _restore_globals(self):
        sandbox.PROJECT_DIRECTORY = self.old_sandbox_project
        sandbox.SANDBOX_DIRECTORY = self.old_sandbox_root
        live_apply.PROJECT_DIRECTORY = self.old_apply_project
        live_apply.SANDBOX_DIRECTORY = self.old_apply_root

    def passing_proposal(self):
        proposal, path = sandbox.create_sandbox_proposal("failure-1", "app.py", "Set VALUE to 2")
        proposal, diff = sandbox.create_draft_patch(path, "app.py", "VALUE = 1", "VALUE = 2")
        proposal["status"] = "sandbox_tests_passed"
        (path / "proposal.json").write_text(json.dumps(proposal), encoding="utf-8")
        return proposal, path, diff

    def test_human_approved_proposal_applies_atomically_and_can_roll_back(self):
        proposal, path, _ = self.passing_proposal()
        approved = sandbox.approve_sandbox_proposal(proposal["proposal_id"])
        self.assertEqual(approved["status"], "draft_approved_by_human")

        receipt = live_apply.apply_approved_proposal(proposal["proposal_id"])
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertFalse(receipt["git_authority_used"])
        self.assertTrue((path / receipt["backup_file"]).is_file())

        rolled_back = live_apply.rollback_applied_proposal(proposal["proposal_id"])
        self.assertTrue(rolled_back["rolled_back"])
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_stale_live_target_is_refused_before_application(self):
        proposal, _, _ = self.passing_proposal()
        sandbox.approve_sandbox_proposal(proposal["proposal_id"])
        (self.project / "app.py").write_text("VALUE = 99\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            live_apply.apply_approved_proposal(proposal["proposal_id"])
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 99\n")

    def test_owner_decision_applies_but_reviewer_decision_does_not(self):
        proposal, _, diff = self.passing_proposal()
        auth = AuthService(self.root / "accounts.json")
        auth.bootstrap_owner("owner", "StrongOwner123", True)
        owner = auth.login("owner", "StrongOwner123")
        auth.create_account("developer", "StrongDeveloper123", "developer", owner)
        auth.create_account("reviewer", "StrongReviewer123", "reviewer", owner)
        developer = auth.login("developer", "StrongDeveloper123")
        reviewer = auth.login("reviewer", "StrongReviewer123")
        dashboard = FailureDashboard(auth, self.root / "dashboard.json")

        failure = dashboard.ingest(FailureEvent("sad", "general", "broken", [{"failed": True}], "Set VALUE to 2", ["app.py"]))
        item = dashboard.push_to_development(failure.failure_id, owner, True)
        item = dashboard.approve_isolated_work(item.work_item_id, owner, "source")
        dashboard.start_forge(item.work_item_id, developer)
        request = item.request
        result = ForgeResult(
            str(uuid.uuid4()), request["request_id"], request["correlation_id"], "succeeded",
            (
                Artifact("diff", {"target_file": "app.py", "patch": diff}),
                Artifact("execution_receipt", {"proposal_id": proposal["proposal_id"]}),
            ),
            tests=({"name": "isolated_suite", "passed": True},),
        )
        dashboard.record_forge_result(item.work_item_id, result, developer)
        dashboard.decide(item.work_item_id, "approve", owner)
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertTrue(any(entry.get("event") == "live_patch_applied" for entry in item.evidence))

        live_apply.rollback_applied_proposal(proposal["proposal_id"])
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 1\n")

        proposal2, _, diff2 = self.passing_proposal()
        failure2 = dashboard.ingest(FailureEvent("forge", "general", "second break", [{"failed": True}], "Set VALUE to 2", ["app.py"]))
        item2 = dashboard.push_to_development(failure2.failure_id, owner, True)
        item2 = dashboard.approve_isolated_work(item2.work_item_id, owner, "source")
        dashboard.start_forge(item2.work_item_id, developer)
        request2 = item2.request
        result2 = ForgeResult(
            str(uuid.uuid4()), request2["request_id"], request2["correlation_id"], "succeeded",
            (
                Artifact("diff", {"target_file": "app.py", "patch": diff2}),
                Artifact("execution_receipt", {"proposal_id": proposal2["proposal_id"]}),
            ),
            tests=({"name": "isolated_suite", "passed": True},),
        )
        dashboard.record_forge_result(item2.work_item_id, result2, developer)
        dashboard.decide(item2.work_item_id, "approve", reviewer)
        self.assertEqual((self.project / "app.py").read_text(encoding="utf-8"), "VALUE = 1\n")
        saved2, _ = sandbox.get_sandbox_proposal(proposal2["proposal_id"])
        self.assertEqual(saved2["status"], "sandbox_tests_passed")


if __name__ == "__main__":
    unittest.main()
