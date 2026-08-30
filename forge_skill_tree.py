"""Branching Forge career skill trees for AI, cybersecurity, and technology.

Learners choose a root path, build shared trunk skills, branch into specialties, and complete
progressively harder boss/interview tests. They may switch or backtrack at any time without
losing previously earned mastery.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillNode:
    node_id: str
    label: str
    level: int
    prerequisites: tuple[str, ...]
    challenge_types: tuple[str, ...]
    boss_test: str | None = None


SKILL_TREES = {
    "cybersecurity": {
        "label": "Cybersecurity",
        "trunk": (
            SkillNode("cyber_fundamentals", "Security Fundamentals", 1, (), ("scenario", "technical_explanation")),
            SkillNode("cyber_networks", "Networks & Systems", 2, ("cyber_fundamentals",), ("packet_reasoning", "troubleshooting")),
            SkillNode("cyber_detection", "Detection & Defensive Analysis", 3, ("cyber_networks",), ("log_triage", "security_scenario", "code_review")),
        ),
        "branches": {
            "soc_blue_team": (
                SkillNode("soc_triage", "SOC Triage", 3, ("cyber_detection",), ("alert_analysis", "log_triage")),
                SkillNode("soc_investigation", "Threat Investigation", 4, ("soc_triage",), ("incident_timeline", "evidence_reasoning")),
                SkillNode("soc_boss", "SOC Analyst Interview Boss", 5, ("soc_investigation",), ("security_scenario", "technical_explanation", "behavioral_star"), "Triage a synthetic incident, explain priority, evidence, containment, and escalation decisions."),
            ),
            "dfir": (
                SkillNode("dfir_evidence", "Digital Evidence Reasoning", 3, ("cyber_detection",), ("timeline", "evidence_reasoning")),
                SkillNode("dfir_response", "Incident Response", 4, ("dfir_evidence",), ("containment_plan", "recovery_plan")),
                SkillNode("dfir_boss", "DFIR Interview Boss", 5, ("dfir_response",), ("security_scenario", "technical_explanation", "behavioral_star"), "Reconstruct a synthetic incident timeline and defend containment and recovery choices."),
            ),
            "appsec": (
                SkillNode("appsec_secure_code", "Secure Coding", 3, ("cyber_detection",), ("secure_code_review", "debugging")),
                SkillNode("appsec_threat_model", "Threat Modeling", 4, ("appsec_secure_code",), ("threat_model", "patch_review")),
                SkillNode("appsec_boss", "Application Security Interview Boss", 5, ("appsec_threat_model",), ("code_review", "security_scenario", "system_design"), "Review a synthetic application, identify risk, propose a safe patch, and explain tradeoffs."),
            ),
            "cloud_security": (
                SkillNode("cloud_iam", "Cloud Identity & Access", 3, ("cyber_detection",), ("iam_review", "policy_reasoning")),
                SkillNode("cloud_hardening", "Cloud Hardening", 4, ("cloud_iam",), ("configuration_review", "architecture_review")),
                SkillNode("cloud_boss", "Cloud Security Interview Boss", 5, ("cloud_hardening",), ("security_scenario", "system_design", "technical_explanation"), "Review a synthetic cloud deployment, find privilege/configuration risks, and defend a remediation plan."),
            ),
        },
    },
    "artificial_intelligence": {
        "label": "Artificial Intelligence",
        "trunk": (
            SkillNode("ai_python", "Python & Data Foundations", 1, (), ("coding", "technical_explanation")),
            SkillNode("ai_models", "Model & Evaluation Foundations", 2, ("ai_python",), ("data_reasoning", "model_evaluation")),
            SkillNode("ai_engineering", "AI Engineering Foundations", 3, ("ai_models",), ("debugging", "leetcode_style", "code_review")),
        ),
        "branches": {
            "ml_engineering": (
                SkillNode("ml_pipelines", "ML Pipelines", 3, ("ai_engineering",), ("pipeline_design", "debugging")),
                SkillNode("ml_reliability", "ML Evaluation & Reliability", 4, ("ml_pipelines",), ("model_evaluation", "code_review")),
                SkillNode("ml_boss", "ML Engineer Interview Boss", 5, ("ml_reliability",), ("leetcode_style", "debugging", "system_design", "technical_explanation"), "Build or repair a small model pipeline, evaluate failure modes, and explain architecture tradeoffs."),
            ),
            "ai_application_engineering": (
                SkillNode("ai_apps", "AI Application Building", 3, ("ai_engineering",), ("coding", "evaluation")),
                SkillNode("ai_systems", "RAG, Tools & Human Approval", 4, ("ai_apps",), ("architecture", "code_review", "evaluation_design")),
                SkillNode("ai_apps_boss", "AI Application Engineer Interview Boss", 5, ("ai_systems",), ("leetcode_style", "debugging", "system_design", "technical_explanation"), "Design and debug an AI application with retrieval/tools, evaluation, and explicit human-control boundaries."),
            ),
            "ai_safety_security": (
                SkillNode("ai_threats", "AI Threat Modeling", 3, ("ai_engineering",), ("threat_model", "defensive_review")),
                SkillNode("ai_guardrails", "AI Evaluation & Guardrails", 4, ("ai_threats",), ("evaluation_design", "security_scenario")),
                SkillNode("ai_safety_boss", "AI Safety & Security Interview Boss", 5, ("ai_guardrails",), ("security_scenario", "code_review", "system_design"), "Analyze a synthetic AI system for prompt-injection, authority, data, and evaluation failures and propose mitigations."),
            ),
        },
    },
    "technology": {
        "label": "Technology",
        "trunk": (
            SkillNode("tech_computing", "Computing Foundations", 1, (), ("troubleshooting", "technical_explanation")),
            SkillNode("tech_code", "Programming & Systems", 2, ("tech_computing",), ("coding", "debugging", "leetcode_style")),
            SkillNode("tech_engineering", "Engineering Practice", 3, ("tech_code",), ("testing", "code_review")),
        ),
        "branches": {
            "software_engineering": (
                SkillNode("swe_algorithms", "Algorithms & Data Structures", 3, ("tech_engineering",), ("leetcode_style", "coding")),
                SkillNode("swe_design", "Software Design", 4, ("swe_algorithms",), ("code_review", "system_design")),
                SkillNode("swe_boss", "Software Engineer Interview Boss", 5, ("swe_design",), ("leetcode_style", "debugging", "code_review", "system_design", "behavioral_star"), "Complete an original coding screen, debug a failure, review code, and explain a small system design."),
            ),
            "it_support": (
                SkillNode("it_triage", "Ticket & User Triage", 3, ("tech_engineering",), ("ticket_triage", "communication")),
                SkillNode("it_systems", "Systems Troubleshooting", 4, ("it_triage",), ("troubleshooting", "network_reasoning")),
                SkillNode("it_boss", "IT Support Interview Boss", 5, ("it_systems",), ("troubleshooting", "technical_explanation", "behavioral_star"), "Resolve a realistic synthetic support case, communicate clearly, and explain escalation decisions."),
            ),
            "devops_cloud": (
                SkillNode("devops_ci", "CI/CD & Automation", 3, ("tech_engineering",), ("pipeline_review", "debugging")),
                SkillNode("devops_reliability", "Cloud Reliability", 4, ("devops_ci",), ("architecture", "observability")),
                SkillNode("devops_boss", "DevOps / Cloud Interview Boss", 5, ("devops_reliability",), ("debugging", "system_design", "technical_explanation"), "Diagnose a synthetic deployment failure and design a safer, observable delivery architecture."),
            ),
        },
    },
}


def get_skill_tree(root_id):
    try:
        return SKILL_TREES[root_id]
    except KeyError as exc:
        raise ValueError("Unknown Forge skill-tree root.") from exc


def branch_nodes(root_id, branch_id):
    tree = get_skill_tree(root_id)
    try:
        return tree["branches"][branch_id]
    except KeyError as exc:
        raise ValueError("Unknown Forge skill-tree branch.") from exc


def boss_test(root_id, branch_id):
    nodes = branch_nodes(root_id, branch_id)
    bosses = [node for node in nodes if node.boss_test]
    if len(bosses) != 1:
        raise ValueError("Each career branch must define exactly one boss test.")
    return bosses[0]


def available_branches(root_id):
    return tuple(get_skill_tree(root_id)["branches"].keys())
