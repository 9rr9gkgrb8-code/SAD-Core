import tempfile
import unittest
from pathlib import Path
from unittest import mock

import beta_gate


class BetaGateContractTests(unittest.TestCase):
    def test_missing_repository_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(beta_gate, "ROOT", Path(directory)):
                self.assertEqual(beta_gate.main(), 1)

    def test_alpha_failure_blocks_beta_when_repository_evidence_exists(self):
        with mock.patch("beta_gate.subprocess.run") as run:
            run.return_value.returncode = 1
            self.assertEqual(beta_gate.main(), 1)
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
