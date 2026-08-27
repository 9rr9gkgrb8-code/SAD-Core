import tempfile
import unittest
from pathlib import Path

from release_gate import REQUIRED_PATHS, find_retired_markers, run_release_gate


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_required_paths(self):
        for relative in REQUIRED_PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("clean\n", encoding="utf-8")

    def test_clean_alpha_snapshot_passes(self):
        self.write_required_paths()
        self.assertEqual(run_release_gate(self.root), [])

    def test_retired_private_mode_marker_blocks_release(self):
        self.write_required_paths()
        marker = "adult" + "_mode"
        (self.root / "legacy.py").write_text(f"flag = '{marker}'\n", encoding="utf-8")
        findings = find_retired_markers(self.root)
        self.assertEqual(findings, [("legacy.py", marker)])
        self.assertTrue(any("retired private-mode markers" in item for item in run_release_gate(self.root)))

    def test_missing_alpha_surface_blocks_release(self):
        problems = run_release_gate(self.root)
        self.assertTrue(any("missing required Alpha paths" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
