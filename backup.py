"""Operator CLI for verified SAD runtime backups."""

from __future__ import annotations

import argparse
from pathlib import Path

from backup_manager import create_backup, restore_backup, verify_backup


def parser():
    value = argparse.ArgumentParser(description="Create, verify, or restore SAD private runtime backups.")
    sub = value.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="Create a verified private-state backup ZIP.")
    create.add_argument("path", type=Path)
    verify = sub.add_parser("verify", help="Verify hashes, paths, manifest, and SQLite integrity.")
    verify.add_argument("path", type=Path)
    restore = sub.add_parser("restore", help="Restore a verified backup while SAD is stopped.")
    restore.add_argument("path", type=Path)
    restore.add_argument("--confirm", action="store_true", help="Explicitly approve overwriting current private state.")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "create":
        manifest = create_backup(args.path)
        print(f"SAD BACKUP: CREATED ({manifest['file_count']} files, {manifest['total_bytes']} bytes)")
        print(Path(args.path).expanduser().resolve())
        return 0
    if args.command == "verify":
        manifest = verify_backup(args.path)
        print(f"SAD BACKUP: VERIFIED ({manifest['file_count']} files)")
        return 0
    if args.command == "restore":
        result = restore_backup(args.path, explicitly_approved=args.confirm)
        print(f"SAD RESTORE: COMPLETE ({result['file_count']} files)")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
