"""Grade-aware Forge curriculum scaffolding for high-school learners.

This module keeps the game-first Forge surface while adding grade-specific rigor,
subject tracks, method-first guidance, and explicit verification expectations.
It does not award XP, alter RBAC, or bypass the existing quest/mastery gates.
"""

from dataclasses import asdict, dataclass

from forge_student import homework_to_quest


SUPPORTED_GRADES = (9, 10, 11, 12)

SUBJECT_TRACKS = {
    "math": {
        9: ("Algebra I", "Geometry foundations", "functions and modeling"),
        10: ("Geometry", "Algebra II foundations", "proof and modeling"),
        11: ("Algebra II", "Precalculus", "statistics and modeling"),
        12: ("Precalculus", "Calculus foundations", "statistics and quantitative reasoning"),
    },
    "science": {
        9: ("Biology", "physical science foundations", "scientific reasoning"),
        10: ("Chemistry", "biology extension", "laboratory reasoning"),
        11: ("Physics", "chemistry extension", "data analysis"),
        12: ("Advanced biology/chemistry/physics", "environmental science", "research reasoning"),
    },
    "english": {
        9: ("close reading", "argument basics", "evidence-based writing"),
        10: ("literary analysis", "rhetoric", "research foundations"),
        11: ("American literature", "argumentation", "source evaluation"),
        12: ("advanced composition", "research synthesis", "college/career writing"),
    },
    "history": {
        9: ("world history", "geography", "primary-source reasoning"),
        10: ("world/US history", "cause and effect", "comparative analysis"),
        11: ("US history", "civics/economics", "document-based analysis"),
        12: ("government", "economics", "advanced historical argument"),
    },
}

RIGOR_BY_GRADE = {
    9: "guided high-school foundation",
    10: "intermediate high-school application",
    11: "upper high-school analysis",
    12: "college-readiness synthesis",
}

HINT_POLICY = (
    "diagnostic_question",
    "concept_nudge",
    "method_hint",
    "worked_analogy",
    "worked_example",
    "full_explanation",
)


@dataclass(frozen=True)
class HighSchoolPlan:
    grade: int
    subject: str
    rigor: str
    tracks: tuple[str, ...]
    learning_objective: str
    tutoring_mode: str
    verification_required: bool
    hint_policy: tuple[str, ...]
    mastery_check: str

    def to_dict(self):
        return asdict(self)


def _normalize_subject(subject):
    value = str(subject or "").strip().lower()
    aliases = {
        "ela": "english",
        "language arts": "english",
        "social studies": "history",
        "maths": "math",
    }
    return aliases.get(value, value)


def build_high_school_plan(grade, subject, learning_objective=""):
    """Return a bounded grade-aware tutoring plan for grades 9-12."""
    if isinstance(grade, bool) or not isinstance(grade, int) or grade not in SUPPORTED_GRADES:
        raise ValueError("Forge high-school mode supports grades 9-12 only.")
    normalized = _normalize_subject(subject)
    if normalized not in SUBJECT_TRACKS:
        raise ValueError("Supported high-school subjects are math, science, english, and history.")
    objective = str(learning_objective or "").strip()
    if len(objective) > 10_000:
        raise ValueError("Learning objective is too large.")
    if not objective:
        objective = f"Build grade {grade} mastery in {SUBJECT_TRACKS[normalized][grade][0]}"
    return HighSchoolPlan(
        grade=grade,
        subject=normalized,
        rigor=RIGOR_BY_GRADE[grade],
        tracks=SUBJECT_TRACKS[normalized][grade],
        learning_objective=objective,
        tutoring_mode="method_first_then_mastery",
        verification_required=normalized in {"math", "science", "history"},
        hint_policy=HINT_POLICY,
        mastery_check=(
            "Solve or explain a fresh transfer problem without copying the worked example, "
            "then justify the method or evidence used."
        ),
    )


def high_school_homework_to_quest(grade, subject, assignment, learning_objective=""):
    """Create an existing Forge quest plus grade-aware curriculum metadata."""
    plan = build_high_school_plan(grade, subject, learning_objective)
    quest = homework_to_quest(plan.subject, assignment, plan.learning_objective)
    return {
        "quest": asdict(quest),
        "curriculum": plan.to_dict(),
        "teaching_contract": {
            "do_not_replace_student_thinking": True,
            "teach_method_before_final_answer": True,
            "use_worked_examples_after_hints": True,
            "require_transfer_mastery_check": True,
            "surface_uncertainty_when_unverified": True,
        },
    }
