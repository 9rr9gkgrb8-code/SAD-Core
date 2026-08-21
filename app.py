import json
import re
import subprocess

from personality import (
    detect_conversation_topic,
    detect_topic_detail,
    get_contextual_follow_up,
    get_response,
)
from sandbox import (
    approve_sandbox_proposal,
    create_draft_patch,
    create_sandbox_proposal,
    export_approved_patch,
    get_sandbox_proposal,
    run_sandbox_tests,
    validate_approved_patch,
)
from model_adapter import (
    generate_local_response,
    local_model_is_available,
    local_model_is_configured,
)
from local_preferences import local_preferences_are_configured
from settings import LEVEL_NAMES, load_settings, save_settings
from evaluator import (
    approve_failure,
    build_repair_plans,
    build_repair_summary,
    find_repair_candidates,
    get_approved_failure,
    load_failure_records,
    report_failure,
)

def ask_yes_or_no(question):
    while True:
        answer = input(question).lower().strip()

        if answer in ["y", "yes"]:
            return True

        if answer in ["n", "no"]:
            return False

        print("Please eSnter y or n.")


def choose_level():
    print("\nChoose Sasha's dialogue level:")

    for number, name in LEVEL_NAMES.items():
        print(f"{number}: {name}")

    while True:
        choice = input("Enter a level from 0 to 2: ").strip()

        try:
            level = int(choice)

            if level in LEVEL_NAMES:
                return level

            print("Please enter a number from 0 to 2.")

        except ValueError:
            print("Please enter a valid number.")


def ask_for_name():
    while True:
        name = input("What should Sasha call you? ").strip()

        if name:
            return name

        print("Please enter a name.")


def chat(level, settings, show_intro=True):
    if show_intro:
        print(f"\nSasha is using level {level}: {LEVEL_NAMES[level]}")
        print("Type 'help' to see available commands.\n")

    previous_topic = None
    previous_detail = None
    previous_response = None
    conversation_history = []
    use_local_model = False

    while True:
        message = input("You: ").strip()

        if not message:
            print("Sasha: Say something so I can respond.")
            continue

        command = message.lower()

        if command in ["quit", "exit", "bye"]:
            print(f"Sasha: Goodbye, {settings['user_name']}!")
            break

        if command == "help":
            print("\nAvailable commands:")
            print("  help              - Show this command list")
            print("  level             - Show Sasha's current level")
            print("  change level      - Choose a different level")
            print("  level 0-2         - Change directly to that level")
            print("  name              - Show your saved name")
            print("  rename            - Change your saved name")
            print("  preferences status - Check whether local preferences are set up")
            print("  report failure    - Record a mistake for review")
            print("  review failures   - Show recent failure reports")
            print("  repair status     - Group failure patterns for human review")
            print("  repair candidates - Show patterns ready for proposal review")
            print("  repair plans      - Show sandbox-only plans for repair candidates")
            print("  approve failure   - Approve a pending report by ID")
            print("  create proposal   - Create and test an isolated proposal copy")
            print("  draft correction  - Make a reviewable sandbox-only code draft")
            print("  review proposal   - Show a saved sandbox draft and test result")
            print("  approve proposal  - Approve a passing sandbox draft by ID")
            print("  export proposal   - Export an approved draft as a manual patch")
            print("  validate proposal - Check an approved patch without applying it")
            print("  model status      - Check whether a local model is ready")
            print("  local model on    - Use the local model for this session")
            print("  local model off   - Return to Sasha's built-in conversation layer")
            print("  quit              - End the conversation\n")
            continue

        if command == "level":
            print(
                f"Sasha: My current level is {level}: "
                f"{LEVEL_NAMES[level]}."
            )
            continue

        # Recognizes level 2, change level 2, and change level to 2.
        level_match = re.fullmatch(
            r"(?:change\s+)?level(?:\s+to)?\s+([0-2])",
            command
        )

        if level_match:
            level = int(level_match.group(1))
            settings["level"] = level
            save_settings(settings)

            print(
                f"Sasha: My level is now {level}: "
                f"{LEVEL_NAMES[level]}."
            )
            continue

        if command in ["change", "change level"]:
            level = choose_level()
            settings["level"] = level
            save_settings(settings)

            print(
                f"Sasha: My level is now {level}: "
                f"{LEVEL_NAMES[level]}."
            )
            continue

        if command == "name":
            print(
                f"Sasha: I have your name saved as "
                f"{settings['user_name']}."
            )
            continue

        if command == "rename":
            new_name = input("What should Sasha call you? ").strip()

            if new_name:
                settings["user_name"] = new_name
                save_settings(settings)
                print(f"Sasha: Got it. I’ll call you {new_name}.")
            else:
                print("Sasha: Your name was not changed.")

            continue

        if command == "report failure":
            print("\nLet's record the mistake for your review.")
            exact_failure = input("What did Sasha get wrong? ").strip()
            user_correction = input("What should the correct answer be? ").strip()

            if not exact_failure:
                print("Sasha: I need a description of the mistake to record it.")
                continue

            record = report_failure(exact_failure, user_correction)
            print("Sasha: I recorded that failure for your approval.")
            print(f"Sasha: Diagnosis: {record['sad_diagnosis']}")
            print(f"Sasha: Proposed next step: {record['suggested_correction']}\n")
            continue

        if command == "review failures":
            records = load_failure_records()

            if not records:
                print("Sasha: There are no saved failure reports yet.\n")
                continue

            print("\nSasha: Recent failure reports:")
            for record in records[-5:]:
                print(f"  ID: {record['failure_id']}")
                print(f"- {record['timestamp']}: {record['exact_failure']}")
                print(f"  Status: {record['fix_status']}")
                print(f"  Next step: {record['suggested_correction']}")
            print()
            continue

        if command in ["preferences status", "profile status"]:
            if local_preferences_are_configured():
                print("Sasha: Your local preferences are configured.\n")
            else:
                print("Sasha: No local preferences are configured yet. See local_preferences.example.json.\n")
            continue

        if command == "repair status":
            patterns = build_repair_summary()

            if not patterns:
                print("Sasha: There are no failure patterns to review yet.\n")
                continue

            print("\nSasha: Repair Engine evidence summary:")
            for pattern in patterns:
                print(f"- Category: {pattern['category']}")
                print(f"  Reports: {pattern['count']}")
                print(f"  Human-approved reports: {pattern['approved_count']}")
                print(f"  Suggested review: {pattern['recommended_next_step']}")
            print("Sasha: This summary does not create or apply a code change.\n")
            continue

        if command == "repair candidates":
            candidates = find_repair_candidates()

            if not candidates:
                print(
                    "Sasha: No repair candidates yet. A category needs at least two "
                    "human-approved reports before SAD can suggest proposal review.\n"
                )
                continue

            print("\nSasha: Repair candidates ready for proposal review:")
            for candidate in candidates:
                print(f"- Category: {candidate['category']}")
                print(f"  Approved evidence: {candidate['approved_count']} reports")
                print(f"  Suggested review: {candidate['recommended_next_step']}")
            print("Sasha: These are review candidates only. No live change is created.\n")
            continue

        if command == "repair plans":
            plans = build_repair_plans()

            if not plans:
                print("Sasha: No repair plans yet. SAD needs two human-approved reports in one category first.\n")
                continue

            print("\nSasha: Sandbox-only repair plans:")
            for plan in plans:
                targets = ", ".join(plan["target_areas"])
                print(f"- Category: {plan['category']}")
                print(f"  Approved evidence: {plan['approved_evidence']} reports")
                print(f"  Suggested areas: {targets}")
                print(f"  Plan: {plan['plan']}")
                print(f"  Safeguard: {plan['safeguard']}")
            print()
            continue

        if command == "approve failure":
            failure_id = input("Enter the failure report ID to approve: ").strip()
            if not failure_id:
                print("Sasha: I need a failure report ID to continue.\n")
                continue

            approved = ask_yes_or_no(
                "Approve this pending failure report? (y/n): "
            )

            if not approved:
                print("Sasha: No report was approved.\n")
                continue

            record = approve_failure(failure_id)
            if record is None:
                print("Sasha: That report was not found or is not pending approval.\n")
                continue

            print("Sasha: That failure report is approved.")
            print("Sasha: Its suggested correction is ready for a future review.\n")
            continue

        if command == "create proposal":
            failure_id = input("Enter the approved failure report ID: ").strip()
            target_file = input("Choose a target file (app.py, evaluator.py, personality.py, settings.py): ").strip()
            proposal_summary = input("Describe the proposed correction: ").strip()

            if get_approved_failure(failure_id) is None:
                print("Sasha: That report is not approved, so I will not create a proposal.\n")
                continue

            try:
                proposal, sandbox_path = create_sandbox_proposal(
                    failure_id, target_file, proposal_summary
                )
                tested_proposal = run_sandbox_tests(sandbox_path)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                print(f"Sasha: I could not create the isolated proposal: {error}\n")
                continue

            print("Sasha: I created an isolated proposal copy. The live project was not changed.")
            print(f"Sasha: Proposal ID: {proposal['proposal_id']}")
            print(f"Sasha: Sandbox test status: {tested_proposal['status']}\n")
            continue

        if command == "draft correction":
            print("Sasha: I will create a draft only in a sandbox. Your live files will not change.")
            failure_id = input("Enter the approved failure report ID: ").strip()
            target_file = input(
                "Choose a target file (app.py, evaluator.py, personality.py, settings.py): "
            ).strip()
            find_text = input("Paste the exact text to replace: ").strip()
            replacement_text = input("Paste the proposed replacement text: ").strip()

            if get_approved_failure(failure_id) is None:
                print("Sasha: That report is not approved, so I will not create a draft.\n")
                continue

            try:
                proposal, sandbox_path = create_sandbox_proposal(
                    failure_id,
                    target_file,
                    "Human-requested sandbox draft correction.",
                )
                draft, diff = create_draft_patch(
                    sandbox_path, target_file, find_text, replacement_text
                )
                tested_draft = run_sandbox_tests(sandbox_path)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                print(f"Sasha: I could not create the sandbox draft: {error}\n")
                continue

            print("Sasha: I created a sandbox-only draft. Your live project was not changed.")
            print(f"Sasha: Proposal ID: {proposal['proposal_id']}")
            print(f"Sasha: Draft status: {draft['status']}")
            print(f"Sasha: Sandbox test status: {tested_draft['status']}")
            print("Sasha: Review this diff before making any future live change:")
            print(diff or "(No text changed.)")
            print()
            continue

        if command == "review proposal":
            proposal_id = input("Enter the sandbox proposal ID: ").strip()
            try:
                proposal, diff = get_sandbox_proposal(proposal_id)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"Sasha: I could not load that sandbox proposal: {error}\n")
                continue

            print("Sasha: This is a sandbox-only draft. Your live project remains unchanged.")
            print(f"Sasha: Proposal ID: {proposal['proposal_id']}")
            print(f"Sasha: Related failure: {proposal['failure_id']}")
            print(f"Sasha: Target file: {proposal['target_file']}")
            print(f"Sasha: Status: {proposal['status']}")
            print("Sasha: Draft diff:")
            print(diff or "(No draft has been created for this proposal.)")
            print()
            continue

        if command == "approve proposal":
            proposal_id = input("Enter the sandbox proposal ID to approve: ").strip()
            approved = ask_yes_or_no(
                "Approve this tested sandbox draft? (y/n): "
            )
            if not approved:
                print("Sasha: No sandbox draft was approved.\n")
                continue

            try:
                proposal = approve_sandbox_proposal(proposal_id)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"Sasha: I could not approve that sandbox draft: {error}\n")
                continue

            if proposal is None:
                print("Sasha: That draft is not ready. Its sandbox tests must pass first.\n")
                continue

            print("Sasha: That sandbox draft is approved for future manual application.")
            print("Sasha: Your live project has not been changed.\n")
            continue

        if command == "export proposal":
            proposal_id = input("Enter the approved sandbox proposal ID: ").strip()
            try:
                exported_path = export_approved_patch(proposal_id)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"Sasha: I could not export that sandbox patch: {error}\n")
                continue

            print("Sasha: I exported the approved patch for your manual review.")
            print(f"Sasha: Patch file: {exported_path}")
            print("Sasha: I did not apply it to your live project.\n")
            continue

        if command == "validate proposal":
            proposal_id = input("Enter the approved sandbox proposal ID: ").strip()
            try:
                validation = validate_approved_patch(proposal_id)
            except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
                print(f"Sasha: I could not validate that sandbox patch: {error}\n")
                continue

            if validation["is_valid"]:
                print("Sasha: The approved patch matches the current live project.")
                print("Sasha: I only checked it; I did not apply it.\n")
            else:
                print("Sasha: The approved patch no longer matches the live project.")
                print("Sasha: Create a new sandbox draft instead of applying this one.")
                print(validation["details"] or "No extra details were returned.")
            continue

        if command == "model status":
            if not local_model_is_configured():
                print("Sasha: No local model is configured yet. Built-in conversation mode is active.\n")
            elif local_model_is_available():
                print("Sasha: Your local model is ready. Type 'local model on' to use it.\n")
            else:
                print("Sasha: A local model is configured, but it is not running right now.\n")
            continue

        if command == "local model on":
            if local_model_is_available():
                use_local_model = True
                print("Sasha: Local model mode is on for this session.\n")
            else:
                print("Sasha: I cannot reach a configured local model, so built-in conversation mode stays on.\n")
            continue

        if command == "local model off":
            use_local_model = False
            print("Sasha: Built-in conversation mode is on.\n")
            continue

        response = None
        if use_local_model:
            response = generate_local_response(
                message, settings["user_name"], conversation_history
            )

        if response is None:
            response = get_contextual_follow_up(
                message,
                level,
                settings["user_name"],
                previous_topic,
                previous_detail,
                previous_response,
            )

        if response is None:
            response = get_response(
                message, level, settings["user_name"], previous_response
            )

        current_topic = detect_conversation_topic(message)
        if current_topic:
            previous_topic = current_topic
            previous_detail = None

        current_detail = detect_topic_detail(message, previous_topic)
        if current_detail:
            previous_detail = current_detail

        print(f"Sasha: {response}")
        previous_response = response
        conversation_history.extend([("User", message), ("Sasha", response)])


def main():
    settings = load_settings()
    current_level = settings["level"]
    user_name = settings["user_name"].strip()

    print("Welcome to SAD — Sandbox Adaptive Dialogue")

    is_new_user = not user_name

    if is_new_user:
        user_name = ask_for_name()
        settings["user_name"] = user_name
        save_settings(settings)
        print(f"Nice to meet you, {user_name}!")

        change_level = ask_yes_or_no(
            "Would you like to change the level? (y/n): "
        )

        if change_level:
            current_level = choose_level()
            settings["level"] = current_level
            save_settings(settings)
            print("Your settings have been saved.")
    else:
        print(f"Sasha: Welcome back, {user_name}.")

    chat(current_level, settings, show_intro=is_new_user)


if __name__ == "__main__":
    main()
