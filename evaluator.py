"""SAD's first controlled self-correction record keeper."""

import json
import uuid
from datetime import datetime
from pathlib import Path


FAILURES_FILE = Path(__file__).with_name("failures.json")


REPAIR_GUIDANCE = {
    "local_model": "Check the local-model configuration and connection before changing conversation code.",
    "conversation_quality": "Review the relevant conversation context and response behavior before proposing a repair.",
    "safety_guardrails": "Review the safety rule and its tests before proposing a repair.",
    "general": "Collect one more clear example before proposing a repair.",
}

REPAIR_PLAN_TEMPLATES = {
    "local_model": {
        "target_areas": ["model_adapter.py", "app.py"],
        "plan": "Verify the model name, availability check, and fallback message in an isolated sandbox.",
    },
    "conversation_quality": {
        "target_areas": ["personality.py", "sasha_voice.py"],
        "plan": "Review the repeated conversation examples and draft one focused response improvement in an isolated sandbox.",
    },
    "safety_guardrails": {
        "target_areas": ["app.py", "personality.py"],
        "plan": "Review the applicable safety boundary and its tests before drafting any sandbox-only change.",
    },
    "general": {
        "target_areas": ["evaluator.py"],
        "plan": "Collect clearer evidence before selecting a code area for a sandbox-only draft.",
    },
}


def categorize_failure(exact_failure):
    """Assign a cautious category to a report without changing code."""
    text = exact_failure.lower()

    if any(phrase in text for phrase in ["local model", "ollama", "model not"]):
        return "local_model"

    if any(phrase in text for phrase in ["guardrail", "safety", "unsafe"]):
        return "safety_guardrails"

    if any(phrase in text for phrase in ["wrong answer", "conversation", "response", "repeat", "context"]):
        return "conversation_quality"

    return "general"


def build_repair_summary(records=None):
    """Group saved reports into evidence for human-reviewed repairs only."""
    if records is None:
        records = load_failure_records()

    patterns = {}
    for record in records:
        category = categorize_failure(record["exact_failure"])
        pattern = patterns.setdefault(
            category,
            {
                "category": category,
                "count": 0,
                "failure_ids": [],
                "approved_count": 0,
                "recommended_next_step": REPAIR_GUIDANCE[category],
            },
        )
        pattern["count"] += 1
        pattern["failure_ids"].append(record["failure_id"])
        if record["fix_status"] == "approved_by_human":
            pattern["approved_count"] += 1

    return sorted(patterns.values(), key=lambda pattern: (-pattern["count"], pattern["category"]))


def find_repair_candidates(records=None, minimum_approved=2):
    """Return only repeated, human-approved patterns eligible for proposal review."""
    return [
        pattern
        for pattern in build_repair_summary(records)
        if pattern["approved_count"] >= minimum_approved
    ]


def build_repair_plans(records=None):
    """Describe safe next steps for candidates without creating a code change."""
    plans = []
    for candidate in find_repair_candidates(records):
        template = REPAIR_PLAN_TEMPLATES[candidate["category"]]
        plans.append(
            {
                "category": candidate["category"],
                "approved_evidence": candidate["approved_count"],
                "target_areas": template["target_areas"],
                "plan": template["plan"],
                "safeguard": "A human must still choose the exact change, review the diff, and approve any export.",
            }
        )
    return plans


def analyze_failure(exact_failure, user_correction):
    """Create a cautious diagnosis and next step without changing SAD itself."""
    if user_correction:
        return (
            "SAD gave an answer that conflicts with the user's correction.",
            "Review the relevant context before answering a similar question."
        )

    return (
        "SAD received a failure report but needs more corrective information.",
        "Ask the user for the correct outcome before proposing a change."
    )


def create_failure_record(exact_failure, user_correction):
    """Create a pending failure record for human review."""
    diagnosis, suggested_correction = analyze_failure(
        exact_failure, user_correction
    )

    return {
        "failure_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "exact_failure": exact_failure,
        "user_correction": user_correction,
        "sad_diagnosis": diagnosis,
        "suggested_correction": suggested_correction,
        "repair_category": categorize_failure(exact_failure),
        "fix_status": "pending_human_approval",
    }


def save_failure_record(record):
    """Append one failure record without exposing it to the Git repository."""
    with FAILURES_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def load_failure_records():
    """Return saved failure reports without changing them."""
    if not FAILURES_FILE.exists():
        return []

    records = []
    with FAILURES_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def save_failure_records(records):
    """Replace saved records after an explicit human-approved status change."""
    with FAILURES_FILE.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")


def approve_failure(failure_id):
    """Approve one identified pending report without changing SAD's code."""
    records = load_failure_records()

    for record in records:
        if (
            record["failure_id"] == failure_id
            and record["fix_status"] == "pending_human_approval"
        ):
            record["fix_status"] = "approved_by_human"
            record["approved_at"] = datetime.now().isoformat(timespec="seconds")
            save_failure_records(records)
            return record

    return None


def get_approved_failure(failure_id):
    """Return a report only when a human has explicitly approved it."""
    for record in load_failure_records():
        if (
            record["failure_id"] == failure_id
            and record["fix_status"] == "approved_by_human"
        ):
            return record
    return None


def report_failure(exact_failure, user_correction):
    """Create and save a failure report, returning it for Sasha to summarize."""
    record = create_failure_record(exact_failure, user_correction)
    save_failure_record(record)
    return record


def normalize_failure_record(record, source="sad"):
    """Adapt a legacy SAD failure record to the shared dashboard contract."""
    from failure_dashboard import FailureEvent

    return FailureEvent(
        source=source,
        category=record.get("repair_category") or categorize_failure(record["exact_failure"]),
        summary=record["exact_failure"],
        evidence=[{
            "failure_id": record.get("failure_id"),
            "timestamp": record.get("timestamp"),
            "user_correction": record.get("user_correction", ""),
            "diagnosis": record.get("sad_diagnosis", ""),
        }],
        suggested_correction=record.get("suggested_correction", "Review the failure evidence."),
    )
