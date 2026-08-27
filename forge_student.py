"""Game-first learning state and quest mechanics for Forge Student."""

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib


class Rank(str, Enum):
    INITIATE = "Initiate"
    APPRENTICE = "Apprentice"
    JOURNEYMAN = "Journeyman"
    EXPERT = "Expert"
    MASTER = "Master"


RANK_THRESHOLDS = ((0, Rank.INITIATE), (100, Rank.APPRENTICE), (300, Rank.JOURNEYMAN), (700, Rank.EXPERT), (1500, Rank.MASTER))
HINT_LADDER = ("nudge", "stronger_hint", "worked_example", "explanation")


@dataclass
class Quest:
    quest_id: str
    title: str
    subject: str
    objective: str
    challenges: list[str]
    source_type: str = "lesson"
    mastery_threshold: float = 0.8
    boss_check: str = ""


@dataclass
class StudentProgress:
    student_id: str
    xp: int = 0
    mastery: dict[str, float] = field(default_factory=dict)
    completed_quests: list[str] = field(default_factory=list)
    companion_stage: int = 0
    hint_levels: dict[str, int] = field(default_factory=dict)

    @property
    def rank(self):
        return next(rank for threshold, rank in reversed(RANK_THRESHOLDS) if self.xp >= threshold)

    def to_dict(self):
        data = asdict(self)
        data["rank"] = self.rank.value
        return data


def homework_to_quest(subject, assignment, learning_objective=""):
    """Convert supplied homework into a deterministic quest without solving it."""
    if not assignment.strip():
        raise ValueError("Homework content is required.")
    objective = learning_objective.strip() or f"Understand and complete the supplied {subject} work"
    digest = hashlib.sha256(f"{subject}\0{assignment}".encode()).hexdigest()[:12]
    return Quest(
        quest_id=f"homework-{digest}",
        title=f"The {subject.title()} Challenge",
        subject=subject,
        objective=objective,
        challenges=[assignment],
        source_type="homework",
        boss_check=f"Explain the method used for this {subject} challenge in your own words.",
    )


def next_hint(progress, quest_id):
    """Escalate hints one rung at a time and never exceed the ladder."""
    index = progress.hint_levels.get(quest_id, 0)
    rung = HINT_LADDER[min(index, len(HINT_LADDER) - 1)]
    progress.hint_levels[quest_id] = min(index + 1, len(HINT_LADDER) - 1)
    return rung


def complete_quest(progress, quest, score, boss_passed):
    """Award progression only when the mastery and boss gates pass."""
    if not 0 <= score <= 1:
        raise ValueError("Mastery score must be between 0 and 1.")
    previous = progress.mastery.get(quest.subject, 0.0)
    progress.mastery[quest.subject] = max(previous, score)
    mastered = score >= quest.mastery_threshold and boss_passed
    if mastered and quest.quest_id not in progress.completed_quests:
        progress.completed_quests.append(quest.quest_id)
        progress.xp += 100
        progress.companion_stage = min(4, len(progress.completed_quests) // 3)
    return {"mastered": mastered, "xp": progress.xp, "rank": progress.rank.value, "companion_stage": progress.companion_stage}
