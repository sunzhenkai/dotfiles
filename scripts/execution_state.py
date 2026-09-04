#!/usr/bin/env python3
"""Private, atomic execution journals and compatible latest-run summaries."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_protocol  # noqa: E402
from dotf_core.sanitize import sanitize_for_json, sanitize_for_persistence, sanitize_for_terminal  # noqa: E402

STATE_VERSION = 1
SUMMARY_KIND = "run-summary"
JOURNAL_KIND = "run-journal"
RUN_ID_RE = re.compile(r"^run-[0-9]{8}T[0-9]{6}Z-[0-9]+-[0-9a-f]{16}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TERMINAL_ACTION_STATES = {"completed", "failed", "blocked", "not-run", "interrupted"}
ACTION_STATES = TERMINAL_ACTION_STATES | {"pending", "running"}
RESULT_STATES = {"changed", "unchanged", "skipped", "failed", "blocked", "not-run", "interrupted"}
RUN_STATES = {"running", "completed", "failed", "interrupted"}
JOURNAL_KEYS = {
    "version", "kind", "complete", "run_id", "status", "started_at", "updated_at",
    "ended_at", "duration_ms", "os", "profile", "plan_version", "plan_hash",
    "current_action", "actions",
}
SUMMARY_KEYS = {
    "version", "kind", "complete", "run_id", "journal", "journal_hash", "status",
    "started_at", "ended_at", "duration_ms", "os", "profile", "plan_version",
    "plan_hash", "actions",
}
ACTION_KEYS = {
    "index", "module", "action", "status", "result_status", "started_at", "ended_at",
    "duration_ms", "exit_code", "reason_code", "message", "dependency_hash",
}
CURRENT_KEYS = {"index", "module", "action"}


class StateError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StateError(f"重复字段: {key}")
        result[key] = value
    return result


def _state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base / "dotf"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    item = os.lstat(path)
    if not stat.S_ISDIR(item.st_mode) or stat.S_ISLNK(item.st_mode):
        raise StateError(f"状态目录不是安全真实目录: {path}")
    os.chmod(path, 0o700)


def _prepare_state() -> tuple[Path, Path]:
    root = _state_dir()
    _ensure_dir(root)
    runs = root / "runs"
    _ensure_dir(runs)
    return root, runs


def _atomic_write(path: Path, payload: bytes) -> None:
    _ensure_dir(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
        parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    safe = sanitize_for_persistence(value)
    return (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        item = os.lstat(path)
        if not stat.S_ISREG(item.st_mode) or stat.S_ISLNK(item.st_mode):
            raise StateError("状态文件不是安全普通文件")
        if stat.S_IMODE(item.st_mode) & 0o077:
            raise StateError("状态文件权限必须不宽于 0600")
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StateError(f"状态文件损坏: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise StateError("状态文件根必须为对象")
    return value, raw


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise StateError(f"{label} schema 字段不完整或包含未知字段")


def _text(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value or "\n" in value or "\t" in value:
        raise StateError(f"{label} 必须为非空单行字符串")
    return value


def _integer(value: Any, label: str, *, nullable: bool = False) -> int | None:
    if nullable and value is None:
        return None
    if type(value) is not int or value < 0:
        raise StateError(f"{label} 必须为非负整数")
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise StateError(f"{label} 必须为 sha256")
    return value


def _validate_action(value: Any, *, terminal: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StateError("action 必须为对象")
    _exact(value, ACTION_KEYS, "action")
    _integer(value["index"], "action.index")
    _text(value["module"], "action.module")
    if value["action"] not in plan_protocol.ACTION_ORDER:
        raise StateError("action.action 不受支持")
    allowed = TERMINAL_ACTION_STATES if terminal else ACTION_STATES
    if value["status"] not in allowed:
        raise StateError("action.status 不受支持")
    if value["result_status"] is not None and value["result_status"] not in RESULT_STATES:
        raise StateError("action.result_status 不受支持")
    for name in ("started_at", "ended_at", "reason_code", "message"):
        _text(value[name], f"action.{name}", nullable=True)
    _integer(value["duration_ms"], "action.duration_ms", nullable=True)
    _integer(value["exit_code"], "action.exit_code", nullable=True)
    _hash(value["dependency_hash"], "action.dependency_hash")
    if terminal and (value["ended_at"] is None or value["duration_ms"] is None):
        raise StateError("完整摘要中的动作缺少结束时间或耗时")
    return value


def _validate_journal(value: dict[str, Any], *, require_complete: bool | None = None) -> dict[str, Any]:
    _exact(value, JOURNAL_KEYS, "journal")
    if value["version"] != STATE_VERSION or value["kind"] != JOURNAL_KIND:
        raise StateError("journal 版本不兼容")
    if type(value["complete"]) is not bool:
        raise StateError("journal.complete 类型无效")
    if require_complete is not None and value["complete"] is not require_complete:
        raise StateError("journal 未完整结束")
    if not isinstance(value["run_id"], str) or not RUN_ID_RE.fullmatch(value["run_id"]):
        raise StateError("run id 无效")
    if value["status"] not in RUN_STATES:
        raise StateError("run status 无效")
    for name in ("started_at", "updated_at"):
        _text(value[name], name)
    _text(value["ended_at"], "ended_at", nullable=True)
    _integer(value["duration_ms"], "duration_ms", nullable=True)
    _text(value["os"], "os")
    _text(value["profile"], "profile", nullable=True)
    if value["plan_version"] != plan_protocol.PLAN_VERSION:
        raise StateError("journal plan 版本不兼容")
    _hash(value["plan_hash"], "plan_hash")
    current = value["current_action"]
    if current is not None:
        if not isinstance(current, dict):
            raise StateError("current_action 类型无效")
        _exact(current, CURRENT_KEYS, "current_action")
        _integer(current["index"], "current_action.index")
        _text(current["module"], "current_action.module")
        if current["action"] not in plan_protocol.ACTION_ORDER:
            raise StateError("current_action.action 无效")
    actions = value["actions"]
    if not isinstance(actions, list):
        raise StateError("actions 必须为列表")
    for index, action in enumerate(actions, 1):
        _validate_action(action, terminal=value["complete"])
        if action["index"] != index:
            raise StateError("action index 必须连续")
    if value["complete"] and (value["ended_at"] is None or value["current_action"] is not None):
        raise StateError("完整 journal 的结束字段无效")
    return value


def _summary_from_journal(journal: dict[str, Any], journal_raw: bytes) -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "kind": SUMMARY_KIND,
        "complete": True,
        "run_id": journal["run_id"],
        "journal": f"runs/{journal['run_id']}.json",
        "journal_hash": _sha256(journal_raw),
        "status": journal["status"],
        "started_at": journal["started_at"],
        "ended_at": journal["ended_at"],
        "duration_ms": journal["duration_ms"],
        "os": journal["os"],
        "profile": journal["profile"],
        "plan_version": journal["plan_version"],
        "plan_hash": journal["plan_hash"],
        "actions": journal["actions"],
    }


def _validate_summary(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("version") != STATE_VERSION:
        raise StateError(f"报告版本不兼容 (got={value.get('version')!r}, want={STATE_VERSION})")
    if value.get("kind") != SUMMARY_KIND:
        raise StateError("报告 kind 不兼容")
    _exact(value, SUMMARY_KEYS, "summary")
    if value["complete"] is not True:
        raise StateError("最近执行报告未完整结束")
    if not isinstance(value["run_id"], str) or not RUN_ID_RE.fullmatch(value["run_id"]):
        raise StateError("报告 run id 无效")
    if value["journal"] != f"runs/{value['run_id']}.json":
        raise StateError("报告 journal 指针无效")
    _hash(value["journal_hash"], "journal_hash")
    if value["status"] not in RUN_STATES - {"running"}:
        raise StateError("报告运行状态无效")
    for name in ("started_at", "ended_at"):
        _text(value[name], name)
    _integer(value["duration_ms"], "duration_ms")
    _text(value["os"], "os")
    _text(value["profile"], "profile", nullable=True)
    if value["plan_version"] != plan_protocol.PLAN_VERSION:
        raise StateError("报告 plan 版本不兼容")
    _hash(value["plan_hash"], "plan_hash")
    if not isinstance(value["actions"], list):
        raise StateError("报告 actions 必须为列表")
    for index, action in enumerate(value["actions"], 1):
        _validate_action(action, terminal=True)
        if action["index"] != index:
            raise StateError("报告 action index 必须连续")
    return value


def _journal_path(run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise StateError("run id 无效")
    _, runs = _prepare_state()
    return runs / f"{run_id}.json"


def _load_journal(run_id: str) -> tuple[dict[str, Any], bytes, Path]:
    path = _journal_path(run_id)
    value, raw = _read_json(path)
    _validate_journal(value)
    if value["run_id"] != run_id:
        raise StateError("journal run id 不匹配")
    return value, raw, path


def _save_journal(journal: dict[str, Any]) -> tuple[Path, bytes]:
    _validate_journal(journal)
    path = _journal_path(journal["run_id"])
    raw = _json_bytes(journal)
    _atomic_write(path, raw)
    return path, raw


def _write_latest(journal: dict[str, Any], journal_raw: bytes) -> Path:
    root, _ = _prepare_state()
    summary = _summary_from_journal(journal, journal_raw)
    _validate_summary(summary)
    lock_path = root / ".latest.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        latest = root / "last-run.json"
        _atomic_write(latest, _json_bytes(summary))
        return latest
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def load_latest_summary(path: Path | None = None) -> dict[str, Any]:
    root, _ = _prepare_state()
    latest = path or root / "last-run.json"
    if not latest.exists():
        raise StateError(f"无最近执行报告 ({latest})")
    summary, _ = _read_json(latest)
    _validate_summary(summary)
    journal_path = root / summary["journal"]
    journal, journal_raw = _read_json(journal_path)
    _validate_journal(journal, require_complete=True)
    expected = _summary_from_journal(journal, journal_raw)
    if summary != expected:
        raise StateError("最近执行报告与完整 journal 不匹配或已损坏")
    return summary


def _elapsed_ms(start: str, end: str) -> int:
    parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    return max(0, int((parse(end) - parse(start)).total_seconds() * 1000))


def _safe_message(value: Any) -> str | None:
    if value is None:
        return None
    text = sanitize_for_terminal(str(value)).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    return text[:200] or None


def cmd_create(args: argparse.Namespace) -> int:
    document = plan_protocol.validate(plan_protocol.load(Path(args.plan)))
    root, runs = _prepare_state()
    del root
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}-{secrets.token_hex(8)}"
    timestamp = now()
    actions = []
    for item in document["actions"]:
        actions.append({
            "index": item["index"], "module": item["module"], "action": item["action"],
            "status": "pending", "result_status": None, "started_at": None, "ended_at": None,
            "duration_ms": None, "exit_code": None, "reason_code": None, "message": None,
            "dependency_hash": plan_protocol.dependency_digest(document, item["module"]),
        })
    journal = {
        "version": STATE_VERSION, "kind": JOURNAL_KIND, "complete": False,
        "run_id": run_id, "status": "running", "started_at": timestamp,
        "updated_at": timestamp, "ended_at": None, "duration_ms": None,
        "os": document["planned_os"], "profile": document["profile"],
        "plan_version": document["version"], "plan_hash": document["plan_digest"],
        "current_action": None, "actions": actions,
    }
    path, _ = _save_journal(journal)
    if path.parent != runs:
        raise StateError("journal 路径边界无效")
    print(f"{run_id}\t{path}")
    return 0


def _action_at(journal: dict[str, Any], index: int) -> dict[str, Any]:
    if index < 1 or index > len(journal["actions"]):
        raise StateError("action index 超出计划")
    return journal["actions"][index - 1]


def cmd_action_start(args: argparse.Namespace) -> int:
    journal, _, _ = _load_journal(args.run_id)
    if journal["complete"] or journal["status"] != "running":
        raise StateError("run 已结束")
    action = _action_at(journal, args.index)
    if action["status"] != "pending":
        raise StateError("action 不是 pending")
    timestamp = now()
    action["status"] = "running"
    action["started_at"] = timestamp
    journal["current_action"] = {"index": args.index, "module": action["module"], "action": action["action"]}
    journal["updated_at"] = timestamp
    _save_journal(journal)
    return 0


def cmd_action_finish(args: argparse.Namespace) -> int:
    journal, _, _ = _load_journal(args.run_id)
    if journal["complete"]:
        raise StateError("run 已结束")
    action = _action_at(journal, args.index)
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    if not isinstance(payload, dict) or set(payload) - {"result_status", "duration_ms", "exit_code", "reason"}:
        raise StateError("action checkpoint 输入无效")
    status = args.status
    if status not in TERMINAL_ACTION_STATES:
        raise StateError("终态 action status 无效")
    if action["status"] not in {"pending", "running"}:
        raise StateError("action 已结束")
    timestamp = now()
    result_status = payload.get("result_status") or (status if status in RESULT_STATES else None)
    if result_status not in RESULT_STATES:
        raise StateError("result status 无效")
    duration = payload.get("duration_ms", 0)
    exit_code = payload.get("exit_code", 0)
    _integer(duration, "duration_ms")
    _integer(exit_code, "exit_code")
    code = {
        "completed": result_status,
        "failed": "handler-failed",
        "blocked": "dependency-blocked",
        "not-run": "not-run",
        "interrupted": "interrupted",
    }[status]
    reason = payload.get("reason")
    action.update({
        "status": status, "result_status": result_status,
        "started_at": action["started_at"] or timestamp, "ended_at": timestamp,
        "duration_ms": duration, "exit_code": exit_code, "reason_code": code,
        "message": _safe_message(reason) or code,
    })
    journal["current_action"] = None
    journal["updated_at"] = timestamp
    _save_journal(journal)
    return 0


def _finalize(journal: dict[str, Any], status: str) -> tuple[Path, Path]:
    timestamp = now()
    for action in journal["actions"]:
        if action["status"] in {"pending", "running"}:
            interrupted = status == "interrupted" and action["status"] == "running"
            action.update({
                "status": "interrupted" if interrupted else "not-run",
                "result_status": "interrupted" if interrupted else "not-run",
                "started_at": action["started_at"] or timestamp,
                "ended_at": timestamp,
                "duration_ms": _elapsed_ms(action["started_at"], timestamp) if action["started_at"] else 0,
                "exit_code": 130 if interrupted else 0,
                "reason_code": "interrupted" if interrupted else "not-run",
                "message": "interrupted" if interrupted else "not-run",
            })
    journal.update({
        "complete": True, "status": status, "updated_at": timestamp, "ended_at": timestamp,
        "duration_ms": _elapsed_ms(journal["started_at"], timestamp), "current_action": None,
    })
    journal_path, raw = _save_journal(journal)
    latest = _write_latest(journal, raw)
    return journal_path, latest


def cmd_finalize(args: argparse.Namespace) -> int:
    journal, _, _ = _load_journal(args.run_id)
    if journal["complete"]:
        raise StateError("run 已结束")
    if args.status not in {"completed", "failed"}:
        raise StateError("final status 无效")
    journal_path, latest = _finalize(journal, args.status)
    print(f"{journal_path}\t{latest}")
    return 0


def cmd_interrupt(args: argparse.Namespace) -> int:
    journal, _, _ = _load_journal(args.run_id)
    if journal["complete"]:
        return 0
    _finalize(journal, "interrupted")
    return 0


def cmd_emit_json(args: argparse.Namespace) -> int:
    journal, raw, _ = _load_journal(args.run_id)
    if not journal["complete"]:
        raise StateError("run 未结束")
    payload = _summary_from_journal(journal, raw)
    counts = {"changed": 0, "unchanged": 0, "skipped": 0, "failed": 0, "blocked": 0, "not_run": 0, "interrupted": 0}
    for action in payload["actions"]:
        result = action["result_status"]
        key = "not_run" if result == "not-run" else result
        if key in counts:
            counts[key] += 1
    payload["summary"] = counts
    print(json.dumps(sanitize_for_json(payload), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def cmd_load_latest(args: argparse.Namespace) -> int:
    summary = load_latest_summary(Path(args.path) if args.path else None)
    print(json.dumps(sanitize_for_json(summary), ensure_ascii=False, sort_keys=True))
    return 0


def cmd_sanitize_file(args: argparse.Namespace) -> int:
    data = Path(args.path).read_text(encoding="utf-8", errors="replace")
    sys.stdout.write(sanitize_for_terminal(data))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="dotf execution state")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--plan", required=True)
    create.set_defaults(func=cmd_create)
    start = sub.add_parser("action-start")
    start.add_argument("--run-id", required=True)
    start.add_argument("--index", type=int, required=True)
    start.set_defaults(func=cmd_action_start)
    finish = sub.add_parser("action-finish")
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--index", type=int, required=True)
    finish.add_argument("--status", required=True)
    finish.set_defaults(func=cmd_action_finish)
    final = sub.add_parser("finalize")
    final.add_argument("--run-id", required=True)
    final.add_argument("--status", required=True)
    final.set_defaults(func=cmd_finalize)
    interrupted = sub.add_parser("interrupt")
    interrupted.add_argument("--run-id", required=True)
    interrupted.set_defaults(func=cmd_interrupt)
    emitted = sub.add_parser("emit-json")
    emitted.add_argument("--run-id", required=True)
    emitted.set_defaults(func=cmd_emit_json)
    loaded = sub.add_parser("load-latest")
    loaded.add_argument("--path")
    loaded.set_defaults(func=cmd_load_latest)
    sanitize_file = sub.add_parser("sanitize-file")
    sanitize_file.add_argument("path")
    sanitize_file.set_defaults(func=cmd_sanitize_file)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.func(args)
    except (StateError, plan_protocol.ProtocolError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"错误: {sanitize_for_terminal(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
