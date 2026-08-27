"""Operator preflight for the local SAD + Forge Alpha."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

from release_gate import run_release_gate


PINNED_IMAGE = re.compile(r"^[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$")
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class Check:
    name: str
    scope: str
    status: str
    detail: str


def check_python(version_info=None):
    version = sys.version_info if version_info is None else version_info
    supported = tuple(version[:2]) >= (3, 11)
    detail = f"Python {version[0]}.{version[1]}"
    return Check("python", "core", "pass" if supported else "block", detail)


def check_release_integrity():
    problems = run_release_gate()
    if problems:
        return Check("release_integrity", "core", "block", "; ".join(problems))
    return Check("release_integrity", "core", "pass", "Alpha release gate passes")


def check_local_model(env=None):
    env = os.environ if env is None else env
    model = env.get("SAD_LOCAL_MODEL", "").strip()
    raw_url = env.get("SAD_LOCAL_MODEL_URL", "").strip()
    if not model and not raw_url:
        return Check("local_model", "optional", "warn", "not configured; generated study output is unavailable")
    if not model or not raw_url:
        return Check("local_model", "core", "block", "set both SAD_LOCAL_MODEL and SAD_LOCAL_MODEL_URL, or neither")
    parsed = urlparse(raw_url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        return Check("local_model", "core", "block", "model URL must use HTTP loopback only")
    return Check("local_model", "optional", "pass", f"configured for {parsed.hostname}")


def check_repair_isolation(env=None, which=shutil.which, runner=subprocess.run):
    env = os.environ if env is None else env
    image = env.get("SAD_SANDBOX_IMAGE", "").strip()
    docker = which("docker")
    if not docker:
        return Check("repair_isolation", "repair", "warn", "Docker is not installed or not on PATH")
    if not PINNED_IMAGE.fullmatch(image):
        return Check("repair_isolation", "repair", "warn", "SAD_SANDBOX_IMAGE must be an exact name@sha256 digest")
    try:
        result = runner(
            [docker, "image", "inspect", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return Check("repair_isolation", "repair", "warn", f"Docker image inspection failed: {error}")
    if result.returncode != 0:
        return Check("repair_isolation", "repair", "warn", "configured digest-pinned image is not preloaded locally")
    return Check("repair_isolation", "repair", "pass", "Docker and digest-pinned local image are ready")


def run_checks(env=None, version_info=None, which=shutil.which, runner=subprocess.run):
    return [
        check_python(version_info),
        check_release_integrity(),
        check_local_model(env),
        check_repair_isolation(env, which, runner),
    ]


def core_ready(checks):
    return not any(check.scope == "core" and check.status == "block" for check in checks)


def repair_ready(checks):
    return all(check.status == "pass" for check in checks if check.scope == "repair")


def main():
    checks = run_checks()
    for check in checks:
        print(f"[{check.status.upper():5}] {check.name}: {check.detail}")
    print()
    print("ALPHA CORE: READY" if core_ready(checks) else "ALPHA CORE: BLOCKED")
    print("REPAIR ISOLATION: READY" if repair_ready(checks) else "REPAIR ISOLATION: BLOCKED")
    raise SystemExit(0 if core_ready(checks) else 1)


if __name__ == "__main__":
    main()
