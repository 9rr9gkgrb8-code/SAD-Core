import tempfile
import unittest
from pathlib import Path
from unittest import mock

import beta_gate


class BetaGateContractTests(unittest.TestCase):
    def test_acceptance_parser_rejects_marker_prose_and_requires_all_sections(self):
        with self.assertRaises(ValueError):
            beta_gate.parse_acceptance_record("Human acceptance required before public Beta")

    def test_release_mode_rejects_hold_record(self):
        with mock.patch.dict("os.environ", {"SAD_BETA_RELEASE": "1"}, clear=False), mock.patch("beta_gate.run_stability_gate", return_value=([], {})):
            self.assertEqual(beta_gate.main(), 1)

    def test_missing_repository_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(beta_gate, "ROOT", Path(directory)):
                self.assertEqual(beta_gate.main(), 1)

    def test_alpha_failure_blocks_beta_when_repository_evidence_exists(self):
        with mock.patch("beta_gate.run_stability_gate", return_value=(["blocked"], {})) as gate:
            self.assertEqual(beta_gate.main(), 1)
            gate.assert_called_once_with(root=beta_gate.ROOT)


if __name__ == "__main__":
    unittest.main()
