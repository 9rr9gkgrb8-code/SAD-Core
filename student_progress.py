"""Durable per-student Forge progression state."""

import json
import os
from pathlib import Path

from forge_student import StudentProgress
import threading


class ProgressStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()

    def _load(self):
        if not self.path.exists():
            return {"schema_version": 1, "students": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("students"), dict):
            raise ValueError("Invalid progress store.")
        return data

    def _save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        os.replace(temp, self.path)

    def get(self, student_id):
        with self.lock:
            raw = self._load()["students"].get(student_id)
            if not raw:
                return StudentProgress(student_id)
            raw.pop("rank", None)
            return StudentProgress(**raw)

    def save(self, progress):
        with self.lock:
            data = self._load()
            data["students"][progress.student_id] = progress.to_dict()
            self._save(data)
            return progress
