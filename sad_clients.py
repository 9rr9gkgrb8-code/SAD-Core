"""Small HTTP clients for Personal Study and Forge Student."""

import json
from urllib.request import Request, urlopen
from urllib.parse import urlparse


def _local_base_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
        raise ValueError("SAD clients may connect only to a loopback HTTP API.")
    return value.rstrip("/")


class SadClient:
    def __init__(self, token, base_url="http://127.0.0.1:8765"):
        self.token = token
        self.base_url = _local_base_url(base_url)

    def request(self, method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            self.base_url + path, data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())

    @staticmethod
    def login(username, password, base_url="http://127.0.0.1:8765"):
        base_url = _local_base_url(base_url)
        request = Request(
            base_url + "/v1/auth/login",
            data=json.dumps({"username": username, "password": password}).encode(),
            method="POST", headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())


class PersonalStudyClient(SadClient):
    def plan(self, action, material, **options):
        return self.request("POST", "/v1/study/plan", {"action": action, "material": material, **options})


class ForgeStudentClient(SadClient):
    def homework_quest(self, subject, assignment, learning_objective=""):
        return self.request("POST", "/v1/forge/quests", {"subject": subject, "assignment": assignment, "learning_objective": learning_objective})

    def progress(self):
        return self.request("GET", "/v1/forge/progress")

    def hint(self, quest_id):
        return self.request("POST", "/v1/forge/hint", {"quest_id": quest_id})

    def complete(self, quest, score, boss_passed):
        return self.request("POST", "/v1/forge/complete", {"quest": quest, "score": score, "boss_passed": boss_passed})
