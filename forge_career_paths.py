"""Flexible Forge career paths for AI, cybersecurity, and technology learners.

Progress is based on demonstrated skill levels, not school grade. Learners can branch into a
specialty, backtrack, switch specialties, and retain earned mastery. Cyber exercises must use
synthetic/local data and authorized sandbox targets only.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CareerTrack:
    track_id: str
    label: str
    family: str
    description: str
    challenge_types: tuple[str, ...]
    safety_boundary: str = "synthetic_or_authorized_sandbox_only"


LEVELS = {
    1: "Explorer",
    2: "Foundation",
    3: "Practitioner",
    4: "Specialist",
    5: "Career Ready",
}

CYBER_TRACKS = {
    "security_foundations": CareerTrack("security_foundations", "Security Foundations", "cybersecurity", "Security principles, identity, risk, hardening, and safe computing.", ("scenario", "log_review", "configuration_review")),
    "soc_blue_team": CareerTrack("soc_blue_team", "SOC / Blue Team", "cybersecurity", "Detection, triage, defensive analysis, alert reasoning, and incident documentation.", ("log_triage", "alert_analysis", "incident_timeline")),
    "dfir": CareerTrack("dfir", "DFIR / Incident Response", "cybersecurity", "Evidence handling, incident reasoning, containment choices, and recovery planning.", ("timeline", "evidence_reasoning", "containment_plan")),
    "cloud_security": CareerTrack("cloud_security", "Cloud Security", "cybersecurity", "Identity, least privilege, configuration review, secrets handling, and cloud risk.", ("iam_review", "policy_reasoning", "configuration_review")),
    "appsec": CareerTrack("appsec", "Application Security", "cybersecurity", "Secure coding, threat modeling, code review, dependency risk, and defensive testing.", ("secure_code_review", "threat_model", "patch_review")),
    "network_security": CareerTrack("network_security", "Network Security", "cybersecurity", "Network fundamentals, segmentation, traffic reasoning, firewall policy, and monitoring.", ("packet_reasoning", "segmentation_design", "firewall_review")),
    "governance_risk": CareerTrack("governance_risk", "GRC / Security Governance", "cybersecurity", "Risk assessment, policy, controls, audit evidence, and security communication.", ("risk_register", "control_mapping", "policy_review")),
    "security_engineering": CareerTrack("security_engineering", "Security Engineering", "cybersecurity", "Design and evaluate secure systems with explicit trust and authority boundaries.", ("architecture_review", "failure_analysis", "design_tradeoff")),
}

AI_TRACKS = {
    "ai_foundations": CareerTrack("ai_foundations", "AI Foundations", "artificial_intelligence", "Python, data reasoning, model concepts, evaluation, and responsible AI.", ("coding", "data_reasoning", "model_evaluation")),
    "ml_engineering": CareerTrack("ml_engineering", "Machine Learning Engineering", "artificial_intelligence", "Data pipelines, training/evaluation concepts, debugging, testing, and deployment reasoning.", ("coding", "debugging", "pipeline_design")),
    "ai_application_engineering": CareerTrack("ai_application_engineering", "AI Application Engineering", "artificial_intelligence", "Build and evaluate applications that use models, retrieval, tools, and human approval boundaries.", ("coding", "architecture", "evaluation")),
    "ai_safety_security": CareerTrack("ai_safety_security", "AI Safety & Security", "artificial_intelligence", "Prompt-injection defense, evaluation, access boundaries, model/system risk, and human oversight.", ("threat_model", "defensive_review", "evaluation_design")),
}

TECH_TRACKS = {
    "software_engineering": CareerTrack("software_engineering", "Software Engineering", "technology", "Algorithms, data structures, debugging, testing, code review, and system design.", ("leetcode_style", "debugging", "code_review", "system_design")),
    "it_support": CareerTrack("it_support", "IT / Help Desk", "technology", "Troubleshooting, networking, operating systems, customer communication, and escalation.", ("ticket_triage", "troubleshooting", "communication")),
    "devops_cloud": CareerTrack("devops_cloud", "DevOps / Cloud", "technology", "Automation, CI/CD, observability, deployment reasoning, reliability, and cloud fundamentals.", ("debugging", "pipeline_review", "architecture")),
    "data_engineering": CareerTrack("data_engineering", "Data Engineering", "technology", "SQL, data modeling, transformations, pipelines, reliability, and performance reasoning.", ("sql", "coding", "pipeline_debugging")),
}

CAREER_TRACKS = {**CYBER_TRACKS, **AI_TRACKS, **TECH_TRACKS}

PATH_ROOTS = {
    "cybersecurity": tuple(CYBER_TRACKS),
    "artificial_intelligence": tuple(AI_TRACKS),
    "technology": tuple(TECH_TRACKS),
}

INTERVIEW_CHALLENGE_TYPES = (
    "leetcode_style", "debugging", "code_review", "system_design", "security_scenario",
    "technical_explanation", "behavioral_star",
)
MAX_PATH_HISTORY = 100


def get_career_track(track_id):
    try:
        return CAREER_TRACKS[track_id]
    except KeyError as exc:
        raise ValueError("Unknown Forge career track.") from exc


def career_labels():
    return {key: track.label for key, track in CAREER_TRACKS.items()}


def specialties(family):
    """Return every specialty available from a path root."""
    try:
        return tuple(get_career_track(track_id) for track_id in PATH_ROOTS[family])
    except KeyError as exc:
        raise ValueError("Unknown Forge career path family.") from exc


def level_label(level):
    try:
        return LEVELS[level]
    except KeyError as exc:
        raise ValueError("Forge career level must be 1-5.") from exc


def switch_path(progress, new_track_id):
    """Switch specialties without deleting prior mastery or completed work.

    progress is a mutable mapping so UI/session layers can persist the navigation history.
    """
    get_career_track(new_track_id)
    previous = progress.get("active_track")
    progress.setdefault("path_history", [])
    if previous and previous != new_track_id:
        progress["path_history"].append(previous)
        del progress["path_history"][:-MAX_PATH_HISTORY]
    progress["active_track"] = new_track_id
    progress.setdefault("track_mastery", {})
    return progress


def backtrack_path(progress):
    """Return to the most recent specialty while preserving all mastery."""
    history = progress.setdefault("path_history", [])
    if not history:
        return progress
    current = progress.get("active_track")
    previous = history.pop()
    if current and current != previous:
        progress.setdefault("visited_tracks", [])
        if current not in progress["visited_tracks"]:
            progress["visited_tracks"].append(current)
            del progress["visited_tracks"][:-MAX_PATH_HISTORY]
    progress["active_track"] = previous
    return progress


def interview_mix(track_id, level):
    """Return interview practice based on demonstrated skill level, never school grade."""
    level_label(level)
    track = get_career_track(track_id)
    base = ["technical_explanation"]
    if level >= 2:
        base.append("debugging")
    if track.family in {"technology", "artificial_intelligence"} and level >= 2:
        base.append("leetcode_style")
    if (track.family == "cybersecurity" or track.track_id == "ai_safety_security") and level >= 2:
        base.append("security_scenario")
    if level >= 3:
        base.append("code_review")
    if level >= 4:
        base.append("system_design")
    if level >= 5:
        base.append("behavioral_star")
    return tuple(dict.fromkeys(base))


def challenge_rules():
    return {
        "leetcode_style": "Generate original interview-style algorithm problems; never copy proprietary question text.",
        "company_style": "Model the skill category and interview format, not confidential or proprietary company questions.",
        "cyber": "Use synthetic data, local labs, CTF-style puzzles, or explicitly authorized sandbox targets only.",
        "grading": "Score reasoning, tests, edge cases, debugging, communication, and solution quality, not answer memorization.",
        "ai_assistance": "Include both no-assistance fundamentals and AI-augmented review/debug/design challenges.",
        "path_freedom": "Learners may change specialties or backtrack at any time without losing earned mastery.",
    }
