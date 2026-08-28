"""Operator CLI for verified encrypted SAD runtime backups."""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path

from backup_manager import (
    create_backup,
    create_portable_backup,
    encrypt_legacy_backup,
    restore_backup,
    verify_backup,
)


def parser():
    value = argparse.ArgumentParser(description="Create, verify, restore, or migrate SAD private runtime backups.")
    sub = value.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="Create a verified Windows-DPAPI-protected backup.")
    create.add_argument("path", type=Path)
    verify = sub.add_parser("verify", help="Decrypt and verify a native backup.")
    verify.add_argument("path", type=Path)
    restore = sub.add_parser("restore", help="Restore a verified native backup while SAD is stopped.")
    restore.add_argument("path", type=Path)
    restore.add_argument("--confirm", action="store_true", help="Explicitly approve overwriting current private state.")
    migrate = sub.add_parser("encrypt-legacy", help="Convert a verified legacy plaintext ZIP to a DPAPI backup.")
    migrate.add_argument("source", type=Path)
    migrate.add_argument("destination", type=Path)

    portable_create = sub.add_parser(
        "portable-create",
        help="Create a passphrase-encrypted cross-profile disaster-recovery backup.",
    )
    portable_create.add_argument("path", type=Path)
    portable_verify = sub.add_parser("portable-verify", help="Verify a portable encrypted backup.")
    portable_verify.add_argument("path", type=Path)
    portable_restore = sub.add_parser(
        "portable-restore",
        help="Restore a portable backup and re-protect runtime state for this Windows user.",
    )
    portable_restore.add_argument("path", type=Path)
    portable_restore.add_argument(
        "--confirm", action="store_true", help="Explicitly approve overwriting current private state."
    )
    return value


def _new_passphrase():
    first = getpass("Portable backup passphrase: ")
    second = getpass("Confirm portable backup passphrase: ")
    if first != second:
        raise ValueError("Portable backup passphrases did not match.")
    return first


def _existing_passphrase():
    return getpass("Portable backup passphrase: ")


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "create":
        manifest = create_backup(args.path)
        print(
            f"SAD BACKUP: CREATED ({manifest['file_count']} files, "
            f"{manifest['total_bytes']} bytes, {manifest['container_protection']})"
        )
        print(Path(args.path).expanduser().resolve())
        return 0
    if args.command == "verify":
        manifest = verify_backup(args.path)
        print(f"SAD BACKUP: VERIFIED ({manifest['file_count']} files, {manifest['container_protection']})")
        return 0
    if args.command == "restore":
        result = restore_backup(args.path, explicitly_approved=args.confirm)
        print(f"SAD RESTORE: COMPLETE ({result['file_count']} files, {result['container_protection']})")
        return 0
    if args.command == "encrypt-legacy":
        manifest = encrypt_legacy_backup(args.source, args.destination)
        print(f"SAD BACKUP: ENCRYPTED LEGACY ({manifest['file_count']} files, {manifest['container_protection']})")
        print(Path(args.destination).expanduser().resolve())
        return 0
    if args.command == "portable-create":
        manifest = create_portable_backup(args.path, _new_passphrase())
        print(
            f"SAD PORTABLE BACKUP: CREATED ({manifest['file_count']} files, "
            f"{manifest['container_protection']})"
        )
        print(Path(args.path).expanduser().resolve())
        return 0
    if args.command == "portable-verify":
        manifest = verify_backup(args.path, passphrase=_existing_passphrase())
        print(
            f"SAD PORTABLE BACKUP: VERIFIED ({manifest['file_count']} files, "
            f"{manifest['container_protection']})"
        )
        return 0
    if args.command == "portable-restore":
        result = restore_backup(
            args.path,
            explicitly_approved=args.confirm,
            passphrase=_existing_passphrase(),
        )
        print(
            f"SAD PORTABLE RESTORE: COMPLETE ({result['file_count']} files, "
            f"{result['container_protection']})"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
