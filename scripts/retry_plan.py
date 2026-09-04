#!/usr/bin/env python3
"""Select failed candidates from a complete summary and invoke the normal planner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import execution_state  # noqa: E402
import plan_protocol  # noqa: E402
from dotf_core.sanitize import sanitize_for_terminal  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: retry_plan.py <report.json> <out-plan>", file=sys.stderr)
        return 2
    report_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    try:
        summary = execution_state.load_latest_summary(report_path)
    except execution_state.StateError as exc:
        print(f"错误: 最近执行报告不可用: {sanitize_for_terminal(str(exc))}", file=sys.stderr)
        return 2

    failed = [action for action in summary["actions"] if action["status"] == "failed"]
    if not failed:
        print("错误: 最近执行报告中没有 failed 动作", file=sys.stderr)
        return 1

    candidates = [
        {
            "module": action["module"],
            "action": action["action"],
            "dependency_hash": action["dependency_hash"],
        }
        for action in failed
    ]
    candidate_pairs = {(item["module"], item["action"]) for item in candidates}
    if len(candidate_pairs) != len(candidates):
        print("错误: 最近执行报告包含重复 failed 动作", file=sys.stderr)
        return 1

    candidate_fd, candidate_name = tempfile.mkstemp(prefix="dotf-retry-candidates-", suffix=".json")
    os.fchmod(candidate_fd, 0o600)
    try:
        with os.fdopen(candidate_fd, "w", encoding="utf-8") as stream:
            json.dump(candidates, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        command = [
            sys.executable,
            str(Path(__file__).resolve().parent / "planner.py"),
            "plan",
            "--format",
            "machine",
            "--os",
            summary["os"],
            "--retry-candidates",
            candidate_name,
        ]
        if summary["profile"] is not None:
            command.extend(["--profile", summary["profile"]])
        planned = subprocess.run(command, capture_output=True, text=True, check=False)
        if planned.returncode != 0:
            message = sanitize_for_terminal(planned.stderr or planned.stdout or "retry planner failed")
            print(message.rstrip(), file=sys.stderr)
            print("建议: 重新运行正常计划（如 dotf init / 指定模块）", file=sys.stderr)
            return planned.returncode

        temporary = out_path.with_name(f".{out_path.name}.{os.getpid()}.tmp")
        temporary.write_text(planned.stdout, encoding="utf-8")
        os.chmod(temporary, 0o600)
        document = plan_protocol.validate(plan_protocol.load(temporary))
        actual_pairs = {(item["module"], item["action"]) for item in document["actions"]}
        if actual_pairs != candidate_pairs or len(document["actions"]) != len(candidates):
            temporary.unlink(missing_ok=True)
            print("错误: retry planner 产生了候选之外的新动作", file=sys.stderr)
            return 2
        os.replace(temporary, out_path)
        os.chmod(out_path, 0o600)
    except (OSError, plan_protocol.ProtocolError, ValueError) as exc:
        print(f"错误: retry 计划生成失败: {sanitize_for_terminal(str(exc))}", file=sys.stderr)
        return 2
    finally:
        Path(candidate_name).unlink(missing_ok=True)

    print(f"将重试 {len(candidates)} 个失败动作")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
