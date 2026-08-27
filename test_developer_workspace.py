import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from container_sandbox import SandboxResult
from developer_workspace import (
    DeveloperWorkspaceError,
    DeveloperWorkspaceStore,
    normalize_scope_path,
    suggest_scope,
)


class FakeRunner:
    def __init__(self, returncode=0):
        self.returncode = returncode

    def run_tests(self, workspace):
        return SandboxResult(self.returncode, "suite output\n", "")


class DeveloperWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "web").mkdir()
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / ".git").mkdir()
        (self.root / ".git" / "config").write_text("secret git control\n", encoding="utf-8")
        (self.root / ".github" / "workflows" / "ci.yml").write_text("name: test\n", encoding="utf-8")
        (self.root / "a.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.root / "old.py").write_text("OLD = True\n", encoding="utf-8")
        (self.root / "web" / "app.js").write_text("const value = 1;\n", encoding="utf-8")
        (self.root / "test_sample.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n", encoding="utf-8")
        self.store = DeveloperWorkspaceStore(self.root, self.root / ".sad_dev")

    def implementation(self, edits, summary="implemented"):
        return lambda _prompt: json.dumps({"summary": summary, "edits": edits})

    def test_scope_validation_blocks_control_plane_and_private_data(self):
        self.assertEqual(normalize_scope_path("web/app.js"), "web/app.js")
        for bad in ("../a.py", "/tmp/a.py", ".github/workflows/ci.yml", ".git/config", "accounts.json", ".env", ".sad_dev/x.py"):
            with self.subTest(path=bad), self.assertRaises(DeveloperWorkspaceError):
                normalize_scope_path(bad)

    def test_scope_planner_returns_reviewable_paths_only(self):
        plan = suggest_scope(
            "change the app",
            self.root,
            generator=lambda _prompt: json.dumps({"summary": "small scope", "paths": ["a.py", "web/app.js"]}),
        )
        self.assertEqual(plan["paths"], ["a.py", "web/app.js"])
        with self.assertRaises(DeveloperWorkspaceError):
            suggest_scope(
                "change CI",
                self.root,
                generator=lambda _prompt: json.dumps({"summary": "unsafe", "paths": [".github/workflows/ci.yml"]}),
            )

    def test_workspace_copy_keeps_test_metadata_but_never_git_control(self):
        created = self.store.create("edit a", ["a.py"], "owner-id")
        worktree = self.root / ".sad_dev" / created["workspace_id"] / "worktree"
        self.assertFalse((worktree / ".git").exists())
        self.assertTrue((worktree / ".github" / "workflows" / "ci.yml").is_file())

    def test_multi_file_generation_tests_without_touching_live_project(self):
        created = self.store.create("update two files and add one", ["a.py", "web/app.js", "new.py"], "developer-id")
        result = self.store.execute(
            created["workspace_id"],
            generator=self.implementation([
                {"path": "a.py", "action": "write", "content": "VALUE = 2\n"},
                {"path": "web/app.js", "action": "write", "content": "const value = 2;\n"},
                {"path": "new.py", "action": "write", "content": "NEW = True\n"},
            ]),
            runner=FakeRunner(0),
        )
        self.assertEqual(result["state"], "tests_passed")
        self.assertEqual(set(result["changed_paths"]), {"a.py", "web/app.js", "new.py"})
        self.assertIn("a/a.py", result["diff"])
        self.assertIn("b/web/app.js", result["diff"])
        self.assertEqual((self.root / "a.py").read_text(encoding="utf-8"), "VALUE = 1\n")
        self.assertEqual((self.root / "web" / "app.js").read_text(encoding="utf-8"), "const value = 1;\n")
        self.assertFalse((self.root / "new.py").exists())
        self.assertTrue(result["tests"]["passed"])
        self.assertIn("git_authority_used", [item["event"] for item in result["evidence"]])

    def test_failed_tests_block_live_application(self):
        created = self.store.create("break a file", ["a.py"], "developer-id")
        result = self.store.execute(
            created["workspace_id"],
            generator=self.implementation([{"path": "a.py", "action": "write", "content": "VALUE = 9\n"}]),
            runner=FakeRunner(1),
        )
        self.assertEqual(result["state"], "tests_failed")
        with self.assertRaises(DeveloperWorkspaceError):
            self.store.apply(created["workspace_id"])
        self.assertEqual((self.root / "a.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_apply_and_explicit_rollback_cover_update_create_and_delete(self):
        created = self.store.create("change project", ["a.py", "new.py", "old.py"], "developer-id")
        tested = self.store.execute(
            created["workspace_id"],
            generator=self.implementation([
                {"path": "a.py", "action": "write", "content": "VALUE = 3\n"},
                {"path": "new.py", "action": "write", "content": "NEW = 3\n"},
                {"path": "old.py", "action": "delete"},
            ]),
            runner=FakeRunner(0),
        )
        self.assertEqual(tested["state"], "tests_passed")
        applied = self.store.apply(created["workspace_id"])
        self.assertEqual(applied["state"], "applied")
        self.assertFalse(applied["application"]["git_authority_used"])
        self.assertEqual((self.root / "a.py").read_text(encoding="utf-8"), "VALUE = 3\n")
        self.assertEqual((self.root / "new.py").read_text(encoding="utf-8"), "NEW = 3\n")
        self.assertFalse((self.root / "old.py").exists())
        rolled = self.store.rollback(created["workspace_id"])
        self.assertEqual(rolled["state"], "rolled_back")
        self.assertEqual((self.root / "a.py").read_text(encoding="utf-8"), "VALUE = 1\n")
        self.assertFalse((self.root / "new.py").exists())
        self.assertEqual((self.root / "old.py").read_text(encoding="utf-8"), "OLD = True\n")

    def test_stale_live_source_and_tampered_tested_copy_fail_closed(self):
        created = self.store.create("edit a", ["a.py"], "developer-id")
        self.store.execute(
            created["workspace_id"],
            generator=self.implementation([{"path": "a.py", "action": "write", "content": "VALUE = 4\n"}]),
            runner=FakeRunner(0),
        )
        (self.root / "a.py").write_text("VALUE = 99\n", encoding="utf-8")
        with self.assertRaises(DeveloperWorkspaceError):
            self.store.apply(created["workspace_id"])

        created2 = self.store.create("edit app", ["web/app.js"], "developer-id")
        self.store.execute(
            created2["workspace_id"],
            generator=self.implementation([{"path": "web/app.js", "action": "write", "content": "const value = 8;\n"}]),
            runner=FakeRunner(0),
        )
        worktree = self.root / ".sad_dev" / created2["workspace_id"] / "worktree" / "web" / "app.js"
        worktree.write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(DeveloperWorkspaceError):
            self.store.apply(created2["workspace_id"])

    def test_mid_apply_failure_restores_every_live_file(self):
        created = self.store.create("edit two", ["a.py", "web/app.js"], "developer-id")
        self.store.execute(
            created["workspace_id"],
            generator=self.implementation([
                {"path": "a.py", "action": "write", "content": "VALUE = 5\n"},
                {"path": "web/app.js", "action": "write", "content": "const value = 5;\n"},
            ]),
            runner=FakeRunner(0),
        )
        real_replace = os.replace
        counter = {"apply": 0}

        def flaky_replace(source, target):
            if ".sad-dev-apply-" in Path(source).name:
                counter["apply"] += 1
                if counter["apply"] == 2:
                    raise OSError("synthetic second-file failure")
            return real_replace(source, target)

        with patch("developer_workspace.os.replace", side_effect=flaky_replace):
            with self.assertRaises(OSError):
                self.store.apply(created["workspace_id"])
        self.assertEqual((self.root / "a.py").read_text(encoding="utf-8"), "VALUE = 1\n")
        self.assertEqual((self.root / "web" / "app.js").read_text(encoding="utf-8"), "const value = 1;\n")


if __name__ == "__main__":
    unittest.main()
