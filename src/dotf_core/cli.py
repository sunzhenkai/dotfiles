"""Small command-line bridge for shell callers."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .atomic import atomic_write
from .backup import backup_destination, backup_target, generate_run_id
from .paths import assert_no_symlinks, ensure_directory
from .sanitize import sanitize_text


def _mode(value: str) -> int:
    return int(value, 8)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dotf_core.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run-id")

    check = commands.add_parser("path-check")
    check.add_argument("root")
    check.add_argument("target")
    check.add_argument("--allow-leaf-symlink", action="store_true")

    parent = commands.add_parser("ensure-parent")
    parent.add_argument("root")
    parent.add_argument("target")

    for name in ("backup-dest", "backup"):
        backup = commands.add_parser(name)
        backup.add_argument("source")
        backup.add_argument("backup_root")
        backup.add_argument("run_id")
        backup.add_argument("target_root")
        if name == "backup":
            backup.add_argument("--sensitive", action="store_true")
            backup.add_argument("--remove-source", action="store_true")

    write = commands.add_parser("atomic-write-file")
    write.add_argument("source")
    write.add_argument("target")
    write.add_argument("target_root")
    write.add_argument("--format", choices=("json", "yaml", "toml", "text"), default=None)
    write.add_argument("--mode", type=_mode, default=0o600)
    write.add_argument("--backup-root")
    write.add_argument("--run-id")
    write.add_argument("--sensitive", action="store_true")

    redact = commands.add_parser("sanitize")
    redact.add_argument("value", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-id":
        print(generate_run_id())
    elif args.command == "path-check":
        print(assert_no_symlinks(args.root, args.target, allow_leaf_symlink=args.allow_leaf_symlink))
    elif args.command == "ensure-parent":
        print(ensure_directory(args.root, Path(args.target).expanduser().absolute().parent))
    elif args.command == "backup-dest":
        print(backup_destination(args.source, args.backup_root, args.run_id, args.target_root))
    elif args.command == "backup":
        print(
            backup_target(
                args.source,
                args.backup_root,
                args.run_id,
                args.target_root,
                sensitive=args.sensitive,
                remove_source=args.remove_source,
            )
        )
    elif args.command == "atomic-write-file":
        # Source is caller-produced staging input; do not log its content.
        content = Path(args.source).read_bytes()
        result = atomic_write(
            args.target,
            content,
            root=args.target_root,
            format=args.format,
            mode=args.mode,
            backup_root=args.backup_root,
            run_id=args.run_id,
            sensitive=args.sensitive,
        )
        print(result.status)
    elif args.command == "sanitize":
        value = args.value if args.value is not None else os.sys.stdin.read()
        print(sanitize_text(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
