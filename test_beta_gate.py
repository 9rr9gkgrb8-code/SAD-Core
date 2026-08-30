import tempfile
import unittest
from pathlib import Path
from unittest import mock

import beta_gate


class BetaGateTests(unittest.TestCase):
    def test_required_beta_contract_markers_are_declared(self):
        contract = (Path(__file__).resolve().parent / "BETA.md").read_text(encoding="utf-8")
        for marker in beta_gate.BETA_CONTRACT_MARKERS:
            self.assertIn(marker, contract)

    def test_gate_fails_closed_when_required_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(beta_gate, "ROOT", Path(directory)):
                self.assertEqual(beta_gate.main(), 1)

    def test_gate_requires_alpha_stable_to_pass(self):
        with mock.patch("beta_gate.subprocess.run") as run:
            run.return_value.returncode = 1
            self.assertEqual(beta_gate.main(), 1)
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
