"""Windows-specific readiness checks for SAD deployment hosts."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import tempfile

from alpha_doctor import core_ready, run_checks
from portable_crypto import CRYPTOGRAPHY_PIN, portable_crypto_status
from runtime_database import AT_REST_SCHEME, RuntimeDatabase
from voice_runtime import VoiceRuntime
from windows_crypto import protect_data, unprotect_data


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class WindowsCheck:
    name: str
    status: str
    detail: str


def check_windows(platform_name=None):
    value = platform.system() if platform_name is None else platform_name
    return WindowsCheck("windows_os", "pass" if value == "Windows" else "block", f"platform={value}")


def check_private_data_writable(root=ROOT):
    local_data = Path(root) / "local_data"
    try:
        local_data.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="sad-write-", dir=local_data, delete=True) as handle:
            handle.write(b"ok")
            handle.flush()
        return WindowsCheck("private_data", "pass", "local_data is writable")
    except OSError as error:
        return WindowsCheck("private_data", "block", f"local_data is not writable: {error}")


def check_dpapi():
    if platform.system() != "Windows":
        return WindowsCheck("dpapi", "block", "Windows DPAPI is unavailable on this host")
    try:
        probe = b"sad-windows-doctor-dpapi-probe"
        protected = protect_data(probe, purpose="windows-doctor:v1")
        if probe in protected or unprotect_data(protected, purpose="windows-doctor:v1") != probe:
            return WindowsCheck("dpapi", "block", "DPAPI round-trip or confidentiality probe failed")
    except (OSError, ValueError) as error:
        return WindowsCheck("dpapi", "block", f"DPAPI protection failed: {error}")
    return WindowsCheck("dpapi", "pass", "current-user DPAPI round-trip passed")


def check_portable_backup_crypto():
    status = portable_crypto_status()
    if not status.get("available"):
        return WindowsCheck("portable_backup_crypto", "block", status.get("error", "portable crypto unavailable"))
    if status.get("version") != CRYPTOGRAPHY_PIN:
        return WindowsCheck("portable_backup_crypto", "block", "portable crypto dependency is not the reviewed pin")
    return WindowsCheck(
        "portable_backup_crypto",
        "pass",
        f"AES-256-GCM portable backup dependency pinned at cryptography=={CRYPTOGRAPHY_PIN}",
    )


def check_runtime_database(root=ROOT):
    try:
        path = Path(root) / "local_data" / "sad_runtime.sqlite3"
        protect = platform.system() == "Windows" and Path(root).resolve() == ROOT.resolve()
        database = RuntimeDatabase(path, protect_at_rest=protect)
        ready = database.quick_check()
    except (OSError, ValueError) as error:
        return WindowsCheck("runtime_database", "block", str(error))
    return WindowsCheck("runtime_database", "pass" if ready else "block", "SQLite quick_check passed" if ready else "SQLite quick_check failed")


def check_runtime_protection(root=ROOT):
    if platform.system() != "Windows":
        return WindowsCheck("runtime_encryption", "block", "DPAPI runtime protection requires Windows")
    try:
        database = RuntimeDatabase(
            Path(root) / "local_data" / "sad_runtime.sqlite3", protect_at_rest=True
        )
        status = database.at_rest_status()
    except (OSError, ValueError) as error:
        return WindowsCheck("runtime_encryption", "block", str(error))
    if not status["protected"] or status["scheme"] != AT_REST_SCHEME or not status["active"]:
        return WindowsCheck("runtime_encryption", "block", "runtime database is not using the required DPAPI scheme")
    return WindowsCheck("runtime_encryption", "pass", f"runtime payloads use {AT_REST_SCHEME}")


def check_voice_runtime(env=None, runtime_factory=VoiceRuntime):
    env = os.environ if env is None else env
    stt = env.get("SAD_STT_URL", "").strip()
    tts = env.get("SAD_TTS_URL", "").strip()
    if not stt and not tts:
        return WindowsCheck("voice_runtime", "warn", "STT/TTS not configured; text Voice bridge remains available")
    runtime = runtime_factory(stt_url=stt, tts_url=tts)
    status = runtime.status()
    if stt and not status["stt_ready"]:
        return WindowsCheck("voice_runtime", "warn", "STT configured but not ready")
    if tts and not status["tts_ready"]:
        return WindowsCheck("voice_runtime", "warn", "TTS configured but not ready")
    if bool(stt) != bool(tts):
        return WindowsCheck("voice_runtime", "warn", "configure both STT and TTS for full audio turns")
    return WindowsCheck("voice_runtime", "pass", "loopback STT and TTS report ready")


def run_windows_checks(*, env=None, platform_name=None, root=ROOT):
    alpha_checks = run_checks(env=env)
    windows_checks = [
        check_windows(platform_name),
        check_private_data_writable(root),
        check_dpapi(),
        check_portable_backup_crypto(),
        check_runtime_database(root),
        check_runtime_protection(root),
        check_voice_runtime(env),
    ]
    ready = core_ready(alpha_checks) and not any(check.status == "block" for check in windows_checks)
    return alpha_checks, windows_checks, ready


def main():
    alpha_checks, windows_checks, ready = run_windows_checks()
    for check in alpha_checks:
        print(f"[{check.status.upper():5}] alpha/{check.name}: {check.detail}")
    for check in windows_checks:
        print(f"[{check.status.upper():5}] windows/{check.name}: {check.detail}")
    print()
    print("WINDOWS HOST: READY" if ready else "WINDOWS HOST: BLOCKED")
    raise SystemExit(0 if ready else 1)


if __name__ == "__main__":
    main()
