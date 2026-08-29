"""Publication blocker for known SAD/Forge exploit reproductions.

This file exists only on the quarantined red-team branch. Each test module below is
written to PASS when an exploit is successfully reproduced. Therefore any successful
exploit reproduction means the release is BLOCKED. Test errors are also fail-closed.
"""

from __future__ import annotations

import unittest


EXPLOIT_MODULES = (
    "test_redteam_provenance_laundering",
    "test_redteam_forge_result_spoofing",
    "test_redteam_failure_poisoning",
    "test_redteam_forge_student_integrity",
    "test_redteam_account_lockout_dos",
    "test_redteam_governance_self_edit",
)


class ExploitResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reproduced = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.reproduced.append(self.getDescription(test))


class ExploitRunner(unittest.TextTestRunner):
    resultclass = ExploitResult


def main():
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module in EXPLOIT_MODULES:
        suite.addTests(loader.loadTestsFromName(module))

    result = ExploitRunner(verbosity=2).run(suite)
    if result.errors:
        print("RED TEAM GATE: BLOCKED - attack harness produced errors; security is unproven.")
        return 1
    if result.reproduced:
        print("RED TEAM GATE: BLOCKED - confirmed exploit reproductions:")
        for name in result.reproduced:
            print(f"- {name}")
        return 1

    print("RED TEAM GATE: PASS - no known exploit reproduction succeeded.")
    print("Convert the now-blocked exploit cases into permanent negative regression tests before release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
