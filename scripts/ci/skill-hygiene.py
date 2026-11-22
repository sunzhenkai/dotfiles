#!/usr/bin/env python3
"""CI gate: skill / instructions sources must stay free of private context.

开源仓约束：`agents/skills/**` 与 `agents/instructions/**` 会公开分发，
不允许出现个人主机、内网地址与凭据。本脚本按行扫描文本文件，命中即失败。

用法：
    python3 scripts/ci/skill-hygiene.py [path...]

无参数时扫描仓库内的默认根；显式传入路径时只扫这些路径（测试用）。
退出码：0 干净 / 1 有命中 / 2 用法错误。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOTS = ("agents/skills", "agents/instructions")

_TEXT_SUFFIXES = {
    ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".sh", ".py", ".mdc", "",
}

# (rule_id, regex, 说明)。凭据类只报告前缀，不复述完整值。
RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "private-ip",
        re.compile(
            r"(?<![\d.])("
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|192\.168\.\d{1,3}\.\d{1,3}"
            r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
            r")(?![\d.])"
        ),
        "私有 IPv4 段",
    ),
    (
        "home-path",
        re.compile(r"/(?:Users|home)/(?!linuxbrew/|root/|shared/|workspace/)[A-Za-z0-9._-]+/"),
        "绝对家目录路径（含真实用户名）",
    ),
    (
        "internal-domain",
        re.compile(r"\b[a-z0-9][a-z0-9-]*\.(?:lan|internal|corp|intra)\b", re.IGNORECASE),
        "内网域名后缀",
    ),
    (
        "credential-token",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}"
            r"|AKIA[0-9A-Z]{16}"
            r"|LTAI[0-9A-Za-z]{12,}"
            r"|sk-[A-Za-z0-9_-]{20,}"
            r"|xox[baprs]-[A-Za-z0-9-]{10,})"
        ),
        "凭据/token",
    ),
    (
        "private-key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "私钥块",
    ),
)


def _redact(rule_id: str, match: str) -> str:
    if rule_id in ("credential-token", "private-key"):
        return match[:12] + "…(已脱敏)"
    return match


def _iter_files(path: Path):
    if path.is_file():
        yield path
        return
    for candidate in sorted(path.rglob("*")):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        if candidate.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        yield candidate


def scan(paths: list[Path]) -> list[str]:
    """返回 findings（`path:line: rule: evidence`），不打印。"""
    findings: list[str] = []
    for root in paths:
        if not root.exists():
            findings.append(f"{root}:0: missing-root: 路径不存在")
            continue
        for file_path in _iter_files(root):
            try:
                text = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for rule_id, pattern, _desc in RULES:
                    for match in pattern.finditer(line):
                        findings.append(
                            f"{file_path}:{line_no}: {rule_id}: {_redact(rule_id, match.group(0))}"
                        )
    return findings


def main(argv: list[str]) -> int:
    args = argv[1:]
    if any(arg in ("-h", "--help") for arg in args):
        print(__doc__.strip())
        return 0
    paths = [Path(arg).resolve() for arg in args] or [ROOT / rel for rel in DEFAULT_ROOTS]
    findings = scan(paths)
    for finding in findings:
        print(finding)
    scanned = sum(1 for root in paths if root.exists())
    print(
        f"skill-hygiene: roots={scanned} findings={len(findings)}",
        file=sys.stderr if findings else sys.stdout,
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
