"""Executable adversarial security gate for SAD.

Runs a focused security slice without subprocesses or network access. The normal full
suite still runs separately in CI; Protocol Black is an additional fail-closed gate.
"""

from __future__ import annotations

import sys
import unittest


BLACK_TEST_MODULES = (
    "test_protocol_black",
    "test_security_surface",
    "test_container_sandbox",
    "test_model_adapter",
    "test_mobile_access",
    "test_mobile_gateway",
    "test_platform_clients",
    "test_platform_events",
    "test_memory_store",
    "test_tool_actions",
    "test_developer_workspace",
    "test_developer_workspace_api",
    "test_live_repair",
)


def build_suite():
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module in BLACK_TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(module))
    return suite


def main():
    result = unittest.TextTestRunner(verbosity=2).run(build_suite())
    if result.wasSuccessful():
        print("PROTOCOL BLACK: PASS")
        return 0
    print("PROTOCOL BLACK: BLOCKED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
