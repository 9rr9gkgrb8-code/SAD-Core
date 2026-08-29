"""Executable cooperative system gate for SAD Platform.

Protocol White proves that the intended, authorized product paths work before
Protocol Black attempts to break the same build. It is deliberately separate from
the full suite: White asks "can SAD do the right thing when used correctly?" while
Black asks "does SAD fail safely when used incorrectly or attacked?"

The gate uses existing deterministic unittest modules only. It performs no external
network access, grants no new authority, does not mutate Git, and does not replace
human approval boundaries.
"""

from __future__ import annotations

import unittest


WHITE_TEST_MODULES = (
    # Product startup, identity, and ordinary API use.
    "test_alpha_product",
    "test_api",
    "test_chat_api",
    "test_conversation",
    # Personal learning and Forge Student product flow.
    "test_personal_study",
    "test_forge_student",
    "test_forge_game_ui",
    # Failure -> development -> isolated work -> human decision flow.
    "test_failure_dashboard",
    "test_developer_workspace_api",
    "test_live_repair",
    # Platform discovery, apps/extensions, governed reusable skills, and events.
    "test_platform_api",
    "test_platform_adolescence_api",
    "test_platform_registry",
    "test_platform_extensions",
    "test_skill_library",
    "test_platform_tier2_api",
    "test_platform_tier3_api",
    # Durable state and cross-module contracts.
    "test_runtime_persistence",
    "test_sad_forge_contract",
    "test_tool_actions",
    # User-facing local voice and paired mobile surfaces.
    "test_voice_runtime",
    "test_mobile_pwa",
)


def build_suite():
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module in WHITE_TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(module))
    return suite


def main():
    result = unittest.TextTestRunner(verbosity=2).run(build_suite())
    if result.wasSuccessful():
        print("PROTOCOL WHITE: PASS")
        return 0
    print("PROTOCOL WHITE: BLOCKED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
