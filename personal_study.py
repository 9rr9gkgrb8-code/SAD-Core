"""Request-directed Personal Study behavior for SAD."""

from dataclasses import asdict, dataclass
from enum import Enum


class StudyAction(str, Enum):
    BREAK_DOWN = "break_down"
    TEACH_METHOD = "teach_method"
    WALKTHROUGH = "walkthrough"
    CHECK_WORK = "check_work"
    HINT = "hint"
    DIRECT_ANSWER = "direct_answer"
    PROOFREAD = "proofread"
    EDIT_ESSAY = "edit_essay"
    RUBRIC_REVIEW = "rubric_review"
    EXAMPLE_ESSAY = "example_essay"
    EXPAND_WORD_COUNT = "expand_word_count"


@dataclass(frozen=True)
class StudyRequest:
    action: StudyAction
    material: str
    course: str = ""
    requested_depth: str = "standard"
    target_word_count: int | None = None
    preserve_voice: bool = True
    graded: bool = False


@dataclass(frozen=True)
class StudyPlan:
    action: str
    instruction: str
    boundaries: tuple[str, ...]
    metadata: dict

    def to_dict(self):
        return asdict(self)


ACTION_INSTRUCTIONS = {
    StudyAction.BREAK_DOWN: "Split the problem into knowns, unknowns, and small ordered steps.",
    StudyAction.TEACH_METHOD: "Explain the reusable method, why each step works, and when to use it.",
    StudyAction.WALKTHROUGH: "Work through the material step by step at the requested depth.",
    StudyAction.CHECK_WORK: "Check the supplied work, identify the first error, and explain the correction.",
    StudyAction.HINT: "Give one proportionate hint without forcing a quiz loop or revealing more than requested.",
    StudyAction.DIRECT_ANSWER: "Answer directly, then include concise reasoning unless the user asks for answer-only.",
    StudyAction.PROOFREAD: "Correct grammar, mechanics, and clarity while preserving meaning and voice.",
    StudyAction.EDIT_ESSAY: "Improve structure, flow, clarity, evidence, and transitions while preserving the argument and voice.",
    StudyAction.RUBRIC_REVIEW: "Evaluate each supplied rubric criterion with evidence, gaps, and specific revisions.",
    StudyAction.EXAMPLE_ESSAY: "Provide an original labeled example for learning; use a different topic when requested.",
    StudyAction.EXPAND_WORD_COUNT: "Add useful explanation, examples, context, transitions, or counterpoints before any requested rough-draft padding.",
}


def build_study_plan(request: StudyRequest) -> StudyPlan:
    """Translate the user's requested help into an explicit, non-Socratic plan."""
    if not request.material.strip():
        raise ValueError("Study material is required.")
    if len(request.material) > 1_000_000:
        raise ValueError("Study material exceeds the safe size limit.")
    if request.action == StudyAction.EXPAND_WORD_COUNT:
        if not request.target_word_count or not 1 <= request.target_word_count <= 100_000:
            raise ValueError("A positive target word count is required for expansion.")

    boundaries = [
        "Follow the requested action; do not force a three-question tutoring script.",
        "Do not claim certainty when source material or rubric information is missing.",
    ]
    if request.preserve_voice:
        boundaries.append("Preserve the learner's voice and stated argument.")
    if request.graded:
        boundaries.append(
            "Keep the learner in control of the submitted work and clearly distinguish examples from their submission."
        )

    return StudyPlan(
        action=request.action.value,
        instruction=ACTION_INSTRUCTIONS[request.action],
        boundaries=tuple(boundaries),
        metadata={
            "course": request.course,
            "requested_depth": request.requested_depth,
            "target_word_count": request.target_word_count,
            "graded": request.graded,
        },
    )
