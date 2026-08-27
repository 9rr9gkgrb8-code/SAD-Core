"""Preflight checks for the SAD paired mobile gateway."""

from __future__ import annotations

import os
from pathlib import Path
import ssl

from mobile_gateway import mobile_host_allowed


def mobile_preflight(env=None):
    env = env or os.environ
    results = []
    host = env.get("SAD_MOBILE_HOST", "")
    cert = env.get("SAD_MOBILE_CERT", "")
    key = env.get("SAD_MOBILE_KEY", "")

    if mobile_host_allowed(host):
        results.append(("host", True, f"Private mobile host accepted: {host}"))
    else:
        results.append(("host", False, "Set SAD_MOBILE_HOST to one explicit private/overlay IPv4 address."))

    cert_path = Path(cert).expanduser() if cert else None
    key_path = Path(key).expanduser() if key else None
    cert_ok = bool(cert_path and cert_path.is_file() and not cert_path.is_symlink())
    key_ok = bool(key_path and key_path.is_file() and not key_path.is_symlink())
    results.append(("certificate", cert_ok, "TLS certificate file is ready." if cert_ok else "Set SAD_MOBILE_CERT to a regular certificate file."))
    results.append(("private_key", key_ok, "TLS private key file is ready." if key_ok else "Set SAD_MOBILE_KEY to a regular private-key file."))

    if cert_ok and key_ok:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
            results.append(("tls_pair", True, "Certificate and key load together under TLS 1.2+."))
        except (OSError, ssl.SSLError, ValueError) as error:
            results.append(("tls_pair", False, f"Certificate/key validation failed: {error}"))
    else:
        results.append(("tls_pair", False, "Certificate/key pair cannot be validated yet."))
    return results


def main():
    results = mobile_preflight()
    for name, passed, detail in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    ready = all(passed for _, passed, _ in results)
    print(f"MOBILE GATEWAY: {'READY' if ready else 'BLOCKED'}")
    raise SystemExit(0 if ready else 1)


if __name__ == "__main__":
    main()
