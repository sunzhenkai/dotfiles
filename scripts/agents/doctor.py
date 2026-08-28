#!/usr/bin/env python3
"""统一 agents doctor：skills + env/MCP + tools/browser/security 详细报告。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from common import Catalog, TOOLS
import defaults as skill_defaults
import doctor_impl as env_doctor

STATUS_PASS = env_doctor.STATUS_PASS
STATUS_WARN = env_doctor.STATUS_WARN
STATUS_FAIL = env_doctor.STATUS_FAIL
STATUS_SKIP = env_doctor.STATUS_SKIP
CheckItem = env_doctor.CheckItem
DoctorReport = env_doctor.DoctorReport


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diagnose unified agents environment")
    p.add_argument("--profile", default=None)
    p.add_argument("--tool", default=None, choices=[*TOOLS])
    p.add_argument("--deep", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--verbose", action="store_true", help="文本模式展开全部分组详情")
    p.add_argument("--fail-on", choices=["fail", "warn"], default="fail")
    p.add_argument("--root", type=Path, default=None)
    return p.parse_args(argv)


def check_skills_drift(cat: Catalog, report: DoctorReport) -> None:
    """增强 skills 漂移：按源条目比对共享目标 ~/.agents/skills 是否存在。"""
    sync_sh = cat.root / "scripts" / "agents" / "sync.sh"
    if not sync_sh.is_file():
        report.add("skills", "sync-script", STATUS_FAIL, "找不到 scripts/agents/sync.sh")
        return
    report.add("skills", "sync-script", STATUS_PASS, "统一 agents sync 脚本存在")

    skills_src = cat.root / "agents" / "skills"
    if not skills_src.is_dir():
        report.add("skills", "source", STATUS_FAIL, "agents/skills 不存在")
        return

    skill_ids = sorted(
        p.name for p in skills_src.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
    )

    skill_dest = Path.home() / ".agents" / "skills"
    if not skill_dest.is_dir():
        report.add(
            "skills",
            "skills-dir",
            STATUS_WARN,
            f"skills 目录不存在: {skill_dest}",
            hint="运行 scripts/agents/sync.sh --skills-only",
        )
        return
    missing_skills = [sid for sid in skill_ids if not (skill_dest / sid).exists()]
    if missing_skills:
        report.add(
            "skills",
            "skills-drift",
            STATUS_WARN,
            f"~/.agents/skills 缺少 {len(missing_skills)} 个 skill（例: {', '.join(missing_skills[:3])}）",
            hint="运行 scripts/agents/sync.sh --skills-only",
        )
    else:
        report.add(
            "skills",
            "skills-drift",
            STATUS_PASS,
            f"~/.agents/skills 与源一致（{len(skill_ids)} 项）",
        )

    try:
        defaults = skill_defaults.load_catalog(cat.root)
    except SystemExit as exc:
        msg = str(exc)
        if msg.startswith("error: "):
            msg = msg[7:]
        report.add("skills", "defaults-catalog", STATUS_FAIL, msg)
        return
    report.add(
        "skills",
        "defaults-catalog",
        STATUS_PASS,
        f"默认 skill 清单 {len(defaults)} 项",
    )
    missing_defaults = [
        it["skill"]
        for it in defaults
        if not skill_defaults.dest_skill_md(it["skill"], skill_dest).is_file()
    ]
    if missing_defaults:
        report.add(
            "skills",
            "defaults-drift",
            STATUS_WARN,
            f"~/.agents/skills 缺少默认 skill（{', '.join(missing_defaults)}）",
            hint="运行 scripts/agents/sync.sh --skills-only（需 npx）",
        )
    else:
        report.add(
            "skills",
            "defaults-drift",
            STATUS_PASS,
            f"默认 skill 已安装（{len(defaults)} 项）",
        )


def build_next_steps(items: List[CheckItem]) -> List[str]:
    steps: List[str] = []
    seen: Set[str] = set()
    for it in items:
        if it.status not in (STATUS_WARN, STATUS_FAIL):
            continue
        hint = (it.hint or "").strip()
        if not hint:
            continue
        # 提取可执行建议
        key = hint
        if key in seen:
            continue
        seen.add(key)
        steps.append(hint)
    # 通用兜底
    if any(i.status in (STATUS_WARN, STATUS_FAIL) and i.group in ("mcp", "skills") for i in items):
        fallback = "scripts/agents/sync.sh all"
        if fallback not in seen:
            steps.append(fallback)
    return steps


def summarize(items: List[CheckItem]) -> Dict[str, Any]:
    counts = Counter(i.status for i in items)
    worst = STATUS_PASS
    order = {STATUS_PASS: 0, STATUS_SKIP: 1, STATUS_WARN: 2, STATUS_FAIL: 3}
    for i in items:
        if order.get(i.status, 0) > order.get(worst, 0):
            worst = i.status
    return {
        "status": worst,
        "counts": {
            "pass": counts.get(STATUS_PASS, 0),
            "warn": counts.get(STATUS_WARN, 0),
            "fail": counts.get(STATUS_FAIL, 0),
            "skip": counts.get(STATUS_SKIP, 0),
            "total": len(items),
        },
    }


def format_text(report: DoctorReport, verbose: bool) -> str:
    summary = summarize(report.items)
    problems = [i for i in report.items if i.status in (STATUS_WARN, STATUS_FAIL)]
    next_steps = build_next_steps(report.items)

    lines = [
        f"agents doctor  profile={report.profile}  risk={report.risk}  tool={report.tool or '*'}",
        "",
        "== summary ==",
        f"  status: {summary['status']}",
        "  counts: "
        + ", ".join(f"{k}={v}" for k, v in summary["counts"].items() if k != "total")
        + f"  total={summary['counts']['total']}",
        "",
    ]

    lines.append("== problems ==")
    if not problems:
        lines.append("  (none)")
    else:
        for it in problems:
            extra = f"  → {it.hint}" if it.hint else ""
            lines.append(f"  [{it.status}] {it.group}/{it.id}: {it.message}{extra}")
    lines.append("")

    if next_steps:
        lines.append("== next_steps ==")
        for s in next_steps:
            lines.append(f"  - {s}")
        lines.append("")

    if verbose or not problems:
        lines.append("== checks ==")
        groups: Dict[str, List[CheckItem]] = {}
        for it in report.items:
            groups.setdefault(it.group, []).append(it)
        for g in ("env", "tools", "mcp", "skills", "browser", "security", "agents"):
            items = groups.get(g) or []
            if not items:
                continue
            lines.append(f"[{g}]")
            for it in items:
                extra = f"  hint: {it.hint}" if it.hint else ""
                lines.append(f"  {it.status:4}  {it.id}: {it.message}{extra}")
            lines.append("")
    else:
        lines.append("（使用 --verbose 查看全量 checks）")

    return "\n".join(lines)


def format_json(report: DoctorReport) -> str:
    summary = summarize(report.items)
    problems = [
        {
            "group": i.group,
            "id": i.id,
            "status": i.status,
            "message": i.message,
            "hint": i.hint,
        }
        for i in report.items
        if i.status in (STATUS_WARN, STATUS_FAIL)
    ]
    payload = {
        "profile": report.profile,
        "tool": report.tool,
        "risk": report.risk,
        "summary": summary,
        "problems": problems,
        "next_steps": build_next_steps(report.items),
        "checks": [asdict(it) for it in report.items],
        "exit_status_meaning": {
            "0": "no fail (warn/skip allowed unless --fail-on warn)",
            "1": "one or more fail (or warn if --fail-on warn)",
        },
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    for key, val in os.environ.items():
        if not val or len(val) < 8:
            continue
        if key.endswith(("API_KEY", "_TOKEN", "_SECRET")) and val in text:
            raise SystemExit("error: JSON 输出意外包含 secret 值，已中止")
    return text + "\n"


def exit_code(report: DoctorReport, fail_on: str) -> int:
    statuses = {i.status for i in report.items}
    if STATUS_FAIL in statuses:
        return 1
    if fail_on == "warn" and STATUS_WARN in statuses:
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    # agents/doctor.py → parents[2] == repo root
    root = args.root.resolve() if args.root else Path(__file__).resolve().parents[2]

    try:
        cat = Catalog(root)
    except SystemExit as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "summary": {"status": "fail", "counts": {"fail": 1, "total": 1}},
                        "problems": [
                            {
                                "group": "mcp",
                                "id": "manifest",
                                "status": "fail",
                                "message": str(exc),
                            }
                        ],
                        "next_steps": [],
                        "checks": [],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 1
        raise

    profile = args.profile or cat.default_profile()
    pdata = cat.resolve_profile(profile)
    report = DoctorReport(
        profile=pdata["id"], tool=args.tool, risk=str(pdata.get("risk") or "low")
    )

    env_doctor.check_env(cat, report, profile)
    env_doctor.check_tools(cat, report, profile)
    env_doctor.check_mcp(cat, report, profile, args.tool, args.deep)
    check_skills_drift(cat, report)
    env_doctor.check_browser(cat, report, profile, args.deep)
    env_doctor.check_security(cat, report)
    # 保留轻量 agents 兼容检查（脚本存在性），详细漂移已在 skills
    env_doctor.check_agents(cat, report)

    if args.json:
        sys.stdout.write(format_json(report))
    else:
        print(format_text(report, verbose=args.verbose))
    return exit_code(report, args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
