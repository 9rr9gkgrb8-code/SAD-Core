"""Privacy-minimized observability for SAD's governed end-to-end journey."""

from __future__ import annotations

from collections import Counter


JOURNEY_STAGES = {
    "conversation": ("chat.session.created", "chat.message.created"),
    "knowledge": ("memory.created",),
    "governed_action": ("tool.action.created", "tool.action.decided", "tool.action.completed"),
    "learning": ("forge.quest.created", "forge.quest.completed"),
    "failure_evidence": ("failure.created",),
}


def build_journey_snapshot(platform_events, dashboard, *, event_limit=250):
    """Return counts and readiness without exposing prompts, memory, diffs, or secrets."""
    stream = platform_events.read(after_seq=0, limit=event_limit)
    events = stream["events"]
    counts = Counter(event["event_type"] for event in events)
    stages = {}
    for stage, required_events in JOURNEY_STAGES.items():
        observed = [event_type for event_type in required_events if counts[event_type]]
        stages[stage] = {
            "complete": len(observed) == len(required_events),
            "observed": observed,
            "required": list(required_events),
        }

    failure_states = Counter(item.state for item in dashboard.failures.values())
    work_states = Counter(item.state for item in dashboard.dev_items.values())
    return {
        "schema_version": 1,
        "privacy": "metadata_only",
        "cursor": stream["cursor"],
        "event_count": len(events),
        "event_counts": dict(sorted(counts.items())),
        "stages": stages,
        "failure_states": dict(sorted(failure_states.items())),
        "work_states": dict(sorted(work_states.items())),
        "complete": all(stage["complete"] for stage in stages.values()),
        "limits": {"event_window": event_limit, "truncated": len(events) == event_limit},
    }
