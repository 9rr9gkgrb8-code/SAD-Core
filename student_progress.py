"""Durable per-student Forge progression state."""

from pathlib import Path
import threading

from forge_student import StudentProgress
from runtime_document import RuntimeJSONDocument


PROGRESS_FILENAME = "student_progress.json"
PROGRESS_NAMESPACE = "student_progress"
LEGACY_PROGRESS_FILE = Path(__file__).with_name(PROGRESS_FILENAME)
MAX_PROGRESS_BYTES = 8_000_000
MAX_STUDENTS = 2_000


def _validate_progress_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("students"), dict):
        raise ValueError("Invalid progress store.")
    if len(data["students"]) > MAX_STUDENTS:
        raise ValueError("Progress store contains too many students.")
    for student_id, value in data["students"].items():
        if not isinstance(student_id, str) or not student_id or not isinstance(value, dict):
            raise ValueError("Invalid student progress record.")
    return data


def _is_live_path(path):
    if path is None:
        return True
    try:
        return Path(path).resolve() == LEGACY_PROGRESS_FILE.resolve()
    except OSError:
        return Path(path) == LEGACY_PROGRESS_FILE


class ProgressStore:
    def __init__(self, path=None, database=None):
        self.persistence = RuntimeJSONDocument(
            PROGRESS_FILENAME,
            PROGRESS_NAMESPACE,
            {"schema_version": 1, "students": {}},
            _validate_progress_data,
            MAX_PROGRESS_BYTES,
            path=None if _is_live_path(path) else path,
            database=database,
        )
        self.path = self.persistence.path
        self.lock = threading.RLock()

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    def get(self, student_id):
        with self.lock:
            raw = self._load()["students"].get(student_id)
            if not raw:
                return StudentProgress(student_id)
            raw = dict(raw)
            raw.pop("rank", None)
            return StudentProgress(**raw)

    def save(self, progress):
        with self.lock:
            data = self._load()
            data["students"][progress.student_id] = progress.to_dict()
            self._save(data)
            return progress
