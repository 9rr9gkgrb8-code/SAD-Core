import tempfile
import unittest
from pathlib import Path

from alpha_stable import FORGE, SAD, completion, evaluate_surface, run_stability_gate


class AlphaStableTests(unittest.TestCase):
    def test_current_sad_and_forge_surfaces_are_complete(self):
        for surface in (SAD, FORGE):
            checks = evaluate_surface(surface)
            self.assertTrue(all(ready for _, ready in checks))
            passed, total, percent = completion(checks)
            self.assertEqual((passed, percent), (total, 100))

    def test_missing_requirement_blocks_stability(self):
        with tempfile.TemporaryDirectory() as directory:
            problems, results = run_stability_gate(root=Path(directory))
        self.assertTrue(problems)
        self.assertTrue(any(not ready for checks in results.values() for _, ready in checks))

    def test_completion_never_rounds_an_incomplete_surface_to_100(self):
        checks = [(f"check-{index}", index != 0) for index in range(200)]
        self.assertEqual(completion(checks), (199, 200, 99))


if __name__ == "__main__":
    unittest.main()
