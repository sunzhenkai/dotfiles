#!/usr/bin/env python3
"""Install agents/ skills into every managed agent runtime layout."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_AGENTS = Path(__file__).resolve().parent
_SCRIPTS = _AGENTS.parent
for _path in (_SCRIPTS, _AGENTS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from layouts import (  # noqa: E402
    FIRST_PARTY_IDENTITY,
    LAYOUTS,
    SkillLayout,
    identity_prefix,
    owner_prefix,
    skills_target,
)
from managed_runtime import (
    ADOPT_REASON,
    AgentRuntimeConflict,
    OnConflict,
    OnTakeover,
    RenderSkill,
    adoptable_equivalent,
    apply_skills_plan,
    compile_skills_plan,
    on_conflict_from_env,
    on_takeover_from_env,
    skill_id_from_target,
)

SLASH_RE = re.compile(r"\{\{slash:([a-z0-9-]+)\}\}")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
POSITIONAL_RE = re.compile(r"\$\{\d+\}")


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    """One layout's sync result, with the first conflict for reporting."""

    label: str
    rc: int
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.rc == 0


def summarize(outcomes: List["SyncOutcome"]) -> str:
    """One-line reason naming the failing layout(s) and why."""
    failed = [item for item in outcomes if not item.ok]
    if not failed:
        return ""
    parts = []
    for item in failed:
        parts.append(f"{item.label}: {item.detail}" if item.detail else item.label)
    return "; ".join(parts)


def _relative_target(target: str, base: Path) -> str:
    """`<skill-id>/SKILL.md` reads better in a one-line reason than a basename."""
    try:
        return Path(target).relative_to(base).as_posix()
    except ValueError:
        return target


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def renderers_for(layout: SkillLayout) -> RenderSkill:
    return render_kiro_skill_bytes if layout.render == "kiro" else render_skill_bytes


def _is_indented(line: str) -> bool:
    return bool(line) and (line[0] == " " or line[0] == "\t")


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    m = FM_RE.match(text)
    if not m:
        return {}, text
    raw_fm, body = m.group(1), m.group(2)
    meta: Dict[str, str] = {}
    # Keep nested metadata block as raw text under key "_metadata_block"
    lines = raw_fm.splitlines()
    i = 0
    meta_lines: List[str] = []
    in_meta = False
    while i < len(lines):
        line = lines[i]
        if in_meta:
            if _is_indented(line):
                meta_lines.append(line)
                i += 1
                continue
            in_meta = False
        if line.startswith("metadata:"):
            in_meta = True
            meta_lines = []
            i += 1
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # YAML folded/literal block scalars: description: > / |
            if val in (">", ">-", "|", "|-"):
                block: List[str] = []
                i += 1
                while i < len(lines) and _is_indented(lines[i]):
                    block.append(lines[i].strip())
                    i += 1
                meta[key] = " ".join(block).strip() if val.startswith(">") else "\n".join(block).strip()
                continue
            meta[key] = val
        i += 1
    if meta_lines:
        meta["_metadata_block"] = "\n".join(meta_lines)
    meta["_raw_fm"] = raw_fm
    return meta, body


def fm_get(meta: Dict[str, str], key: str, default: str = "") -> str:
    return meta.get(key, default)


def unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s


def yaml_quote(s: str) -> str:
    """Emit a single-line YAML string safe for frontmatter values."""
    s = unquote(s).replace("\n", " ").strip()
    if not s:
        return '""'
    if any(c in s for c in ':#"\'\\\n') or s.startswith(">") or s.startswith("|") or s[:1] in "|&*!>@`":
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def replace_slashes(body: str) -> str:
    """共享目标下 slash 命令统一渲染为 /xxx。"""
    return SLASH_RE.sub(lambda m: "/" + m.group(1), body)


def render_skill_frontmatter(meta: Dict[str, str], skill_id: str) -> str:
    name = unquote(fm_get(meta, "name", skill_id))
    desc = unquote(fm_get(meta, "description"))
    if not desc:
        raise ValueError(f"skill {skill_id}: description is required (got empty after parse)")
    license_ = fm_get(meta, "license")
    compat = fm_get(meta, "compatibility")
    lines = [
        f"name: {yaml_quote(name)}",
        f"description: {yaml_quote(desc)}",
    ]
    if license_:
        lines.append(f"license: {yaml_quote(license_)}")
    if compat:
        lines.append(f"compatibility: {yaml_quote(compat)}")
    if meta.get("_metadata_block"):
        lines.append("metadata:")
        lines.append(meta["_metadata_block"])
    return "---\n" + "\n".join(lines) + "\n---\n"


def render_skill_bytes(skill_dir: Path, skill_id: str) -> bytes:
    """Render one SKILL.md without mutating source or destination state."""
    src = skill_dir / "SKILL.md"
    meta, body = parse_frontmatter(src.read_text(encoding="utf-8"))
    body = replace_slashes(body)
    content = render_skill_frontmatter(meta, skill_id) + "\n" + body.lstrip("\n")
    if not content.endswith("\n"):
        content += "\n"
    validate_output(src, content)
    return content.encode("utf-8")


def inject_kiro_arguments(body: str) -> str:
    """Kiro slash skills only receive arguments through an explicit marker."""
    if "$ARGUMENTS" in body or POSITIONAL_RE.search(body):
        return body
    return body.rstrip() + "\n\n$ARGUMENTS\n"


def render_kiro_skill_bytes(skill_dir: Path, skill_id: str) -> bytes:
    """Render one Kiro skill without mutating source or destination state."""
    src = skill_dir / "SKILL.md"
    content = render_skill_bytes(skill_dir, skill_id).decode("utf-8")
    marker = content.find("---\n", 1)
    if marker < 0:
        die(f"{src}: rendered frontmatter is malformed")
    body = content[marker + 4 :]
    content = content[: marker + 4] + inject_kiro_arguments(body)
    validate_output(src, content)
    return content.encode("utf-8")


def validate_output(path: Path, content: str) -> None:
    if SLASH_RE.search(content):
        leftovers = re.findall(r"\{\{slash:[a-z0-9-]+\}\}", content)
        die(f"{path}: residual placeholders: {leftovers}")


def _sync_runtime(
    root: Path,
    base: Path,
    renderer: RenderSkill,
    *,
    owner_prefix: str,
    identity_prefix: str,
    label: str,
    dry_run: bool,
    only_ids: frozenset[str] | None = None,
    on_conflict: OnConflict = "block",
    on_takeover: OnTakeover = "skip",
    verbose: bool = False,
) -> SyncOutcome:
    plan = compile_skills_plan(
        root,
        renderer,
        target_root=base,
        owner_prefix=owner_prefix,
        identity_prefix=identity_prefix,
        only_ids=only_ids,
        on_conflict=on_conflict,
        on_takeover=on_takeover,
    )

    adoptable = {item.target for item in adoptable_equivalent(plan)}
    blocking = [item for item in plan.conflicts if item.target not in adoptable]
    blocked_skills: dict[str, str] = {}
    for item in blocking:
        skill_id = skill_id_from_target(item.target, base) or "?"
        blocked_skills.setdefault(skill_id, item.conflict or "conflict")

    creates = sum(1 for op in plan.operations if op.action == "create" and op.target not in adoptable)
    updates = sum(1 for op in plan.operations if op.action == "update" or op.remediated)
    prunes = sum(1 for op in plan.operations if op.action == "prune")
    adopts = len(adoptable)
    unchanged = sum(1 for op in plan.operations if op.action == "none")
    write_ops = creates + updates
    skip_n = len(blocked_skills)
    total = len(plan.operations)

    print(
        f"==> skills  {label}  {write_ops}↑ {adopts}adopt {skip_n}✗ "
        f"{prunes}-  |  {total} files"
    )
    if blocked_skills:
        reasons = []
        for skill_id, reason in sorted(blocked_skills.items()):
            tag = "unowned" if reason == ADOPT_REASON else reason
            reasons.append(f"{skill_id} ({tag})")
        print(f"  ✗ {', '.join(reasons)}")
        if on_takeover == "skip" and any(
            reason == ADOPT_REASON for reason in blocked_skills.values()
        ):
            print("  hint: backup+takeover with --takeover=backup (TTY will also prompt)")

    if verbose:
        markers = {
            "none": "=",
            "create": "+",
            "update": "+",
            "chmod": "~",
            "prune": "-",
            "block": "!",
        }
        for operation in plan.operations:
            marker = "~" if operation.remediated else markers[operation.action]
            suffix = " (overwrite, backup)" if operation.remediated else ""
            if operation.target in adoptable:
                marker, suffix = "+", " (adopt equivalent)"
            skill_id = skill_id_from_target(operation.target, base)
            if skill_id in blocked_skills and operation.target not in adoptable:
                marker = "!"
            print(f"  {marker} {operation.target}{suffix}")
            if operation.conflict and operation.target not in adoptable and not operation.remediated:
                print(f"    conflict: {operation.conflict}")

    first_conflict = next(
        (
            f"{_relative_target(item.target, base)}: {item.conflict}"
            for item in blocking
        ),
        "",
    )
    if blocked_skills and not first_conflict:
        first_conflict = f"skipped {', '.join(sorted(blocked_skills))}"

    if dry_run:
        print(
            f"  done {label} (plan): changed={write_ops} pruned={prunes} "
            f"unchanged={unchanged} adopt={adopts} conflicts={skip_n}"
        )
        return SyncOutcome(label, 1 if blocked_skills else 0, first_conflict)

    try:
        result = apply_skills_plan(plan, renderer)
    except AgentRuntimeConflict as exc:
        print(f"error: {exc}", file=sys.stderr)
        return SyncOutcome(label, 1, first_conflict or str(exc))
    skipped = result.skipped_skills
    print(
        f"  done {label}: changed={result.changed} pruned={result.pruned} "
        f"unchanged={result.unchanged}"
        + (f" skipped={','.join(skipped)}" if skipped else "")
    )
    detail = first_conflict
    if skipped and not detail:
        detail = f"skipped {', '.join(skipped)}"
    return SyncOutcome(label, 1 if skipped else 0, detail)


def _takeover_candidates(
    root: Path,
    *,
    on_conflict: OnConflict,
) -> list[tuple[str, str]]:
    """Return (layout_label, skill_id) pairs that need Takeover if policy is skip."""
    from desired_set import resolve_skill_desired_set

    desired = resolve_skill_desired_set(root)
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for layout in LAYOUTS:
        plan = compile_skills_plan(
            root,
            renderers_for(layout),
            target_root=skills_target(layout),
            owner_prefix=owner_prefix(layout, "first-party"),
            identity_prefix=identity_prefix(layout, FIRST_PARTY_IDENTITY),
            only_ids=desired,
            on_conflict=on_conflict,
            on_takeover="skip",
        )
        adoptable = {item.target for item in adoptable_equivalent(plan)}
        for operation in plan.conflicts:
            if operation.target in adoptable or operation.conflict != ADOPT_REASON:
                continue
            skill_id = skill_id_from_target(operation.target, plan.target_root)
            if not skill_id:
                continue
            key = (layout.label, skill_id)
            if key not in seen:
                seen.add(key)
                found.append(key)
    return found


def _confirm_takeover(candidates: list[tuple[str, str]]) -> bool:
    skills = sorted({skill_id for _, skill_id in candidates})
    print(
        f"Takeover: {len(skills)} skill(s) have unowned divergent files "
        f"({', '.join(skills)})."
    )
    print("Backup those files under XDG_STATE_HOME/dotf/backups/, then write managed bytes?")
    try:
        answer = input("Takeover with backup? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def sync_layout(
    root: Path,
    layout: SkillLayout,
    *,
    dry_run: bool = False,
    on_conflict: OnConflict | None = None,
    on_takeover: OnTakeover | None = None,
    verbose: bool = False,
) -> SyncOutcome:
    """Sync first-party skills into one layout."""
    from desired_set import resolve_skill_desired_set

    return _sync_runtime(
        root,
        skills_target(layout),
        renderers_for(layout),
        owner_prefix=owner_prefix(layout, "first-party"),
        identity_prefix=identity_prefix(layout, FIRST_PARTY_IDENTITY),
        label=layout.label,
        dry_run=dry_run,
        only_ids=resolve_skill_desired_set(root),
        on_conflict=on_conflict if on_conflict is not None else on_conflict_from_env(),
        on_takeover=on_takeover if on_takeover is not None else on_takeover_from_env(),
        verbose=verbose or os.environ.get("DOTF_VERBOSE", "") == "1",
    )


def sync_skills(
    root: Path,
    dry_run: bool = False,
    on_conflict: OnConflict | None = None,
    on_takeover: OnTakeover | None = None,
    verbose: bool = False,
) -> List[SyncOutcome]:
    conflict = on_conflict if on_conflict is not None else on_conflict_from_env()
    takeover = on_takeover if on_takeover is not None else on_takeover_from_env()
    verbose = verbose or os.environ.get("DOTF_VERBOSE", "") == "1"

    if (
        not dry_run
        and takeover == "skip"
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    ):
        candidates = _takeover_candidates(root, on_conflict=conflict)
        if candidates and _confirm_takeover(candidates):
            takeover = "backup"
            os.environ["DOTF_TAKEOVER"] = "backup"

    return [
        sync_layout(
            root,
            layout,
            dry_run=dry_run,
            on_conflict=conflict,
            on_takeover=takeover,
            verbose=verbose,
        )
        for layout in LAYOUTS
    ]


SHIMS: Dict[str, str] = {}


def install_shims(root: Path, dry_run: bool = False) -> None:
    """Put the canonical script on PATH so mirrored copies never shadow it."""
    bin_dir = Path.home() / ".local" / "bin"
    for name, rel in SHIMS.items():
        canonical = root / rel
        if not canonical.is_file():
            continue
        dest = bin_dir / name
        content = (
            "#!/usr/bin/env sh\n"
            f"# generated by scripts/agents/sync.py; points at the canonical {name}\n"
            f'exec python3 "{canonical}" "$@"\n'
        )
        if dest.is_file() and dest.read_text() == content:
            print(f"  = {dest}")
            continue
        print(f"  + {dest}")
        if dry_run:
            continue
        bin_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        dest.chmod(0o755)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync agents skills into every managed runtime layout (tool 无关)"
    )
    parser.add_argument(
        "tool",
        nargs="?",
        default="all",
        help="仅兼容旧用法，必须省略或为 all（skills 同步已与 tool 无关）",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--on-conflict",
        choices=("block", "backup"),
        default=None,
        help="block（默认）遇到本机改动即跳过该 Skill；backup 先备份再覆写已受管目标的漂移",
    )
    parser.add_argument(
        "--takeover",
        choices=("skip", "backup"),
        default=None,
        dest="on_takeover",
        help="skip（默认）跳过内容不等价的无所有权目标；backup 先备份再接管并登记 ownership",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="逐文件打印（默认只打 Layout 进度摘要）",
    )
    parser.add_argument("--root", type=Path, default=None, help="dotfiles root (default: auto)")
    args = parser.parse_args(argv)

    if args.tool.lower() != "all":
        die(f"skills 同步已与 tool 无关，请直接运行 sync.py（收到: '{args.tool}'）")

    root = args.root.resolve() if args.root else repo_root()

    rc = 0
    try:
        outcomes = sync_skills(
            root,
            dry_run=args.dry_run,
            on_conflict=args.on_conflict,
            on_takeover=args.on_takeover,
            verbose=args.verbose,
        )
        rc = max((item.rc for item in outcomes), default=0)
    except SystemExit as e:
        rc = int(e.code) if e.code else 1
    except Exception as e:
        print(f"error syncing skills: {e}", file=sys.stderr)
        return 1
    if rc == 0:
        print("==> shims")
        install_shims(root, dry_run=args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
