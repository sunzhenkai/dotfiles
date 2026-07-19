#!/usr/bin/env python3
"""从最近执行报告生成仅含 failed 动作的 machine plan。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modules  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: retry_plan.py <report.json> <out-plan>", file=sys.stderr)
        return 2
    report_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    doc = json.loads(report_path.read_text(encoding="utf-8"))

    failed = [a for a in doc.get("actions") or [] if a.get("status") == "failed"]
    if not failed:
        print("错误: 最近报告中没有 failed 动作", file=sys.stderr)
        return 1

    os_id = doc.get("os") or modules.detect_os()
    errors: list[str] = []
    retry_actions: list[tuple[str, str]] = []
    by_name = {m["name"]: m for m in modules.load_registry()}

    for a in failed:
        mod_name = a.get("module")
        action = a.get("action")
        mod = by_name.get(mod_name)
        if mod is None:
            errors.append(f"未知模块: {mod_name}")
            continue
        os_list = mod.get("os")
        if os_list is not None and not isinstance(os_list, list):
            os_list = [os_list]
        if not modules.matches_os(os_list, os_id):
            errors.append(f"模块 {mod_name} 不适用于当前 OS={os_id}")
            continue
        for dep in modules.module_depends_on(mod):
            dmod = by_name.get(dep)
            if dmod is None:
                errors.append(f"{mod_name} 依赖缺失: {dep}")
                continue
            dos = dmod.get("os")
            if dos is not None and not isinstance(dos, list):
                dos = [dos]
            if not modules.matches_os(dos, os_id):
                errors.append(f"{mod_name} 依赖 {dep} 不适用于 OS={os_id}")
        retry_actions.append((str(action), str(mod_name)))

    if errors:
        print("错误: 重试前依赖或适用性校验失败:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("建议: 重新运行完整计划（如 dotf init / 指定模块）", file=sys.stderr)
        return 1

    lines = ["PLAN_OK", f"OS\t{os_id}", "PROFILE\t"]
    for i, (action, mod_name) in enumerate(retry_actions, 1):
        lines.append(f"ACTION\t{i}\t{action}\t{mod_name}\tretry")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"将重试 {len(retry_actions)} 个失败动作")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
