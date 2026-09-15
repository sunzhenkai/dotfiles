#!/usr/bin/env python3
"""Install OpenSpec CLI skills into the shared ~/.agents/skills tree."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from defaults import first_party_skill_ids
from layouts import (
    LAYOUTS,
    OPENSPEC_IDENTITY,
    SHARED_LAYOUT,
    SkillLayout,
    home_for_target,
    identity_prefix,
    layout_for_target,
    owner_prefix,
    skills_target,
)
from managed_runtime import (
    AgentRuntimeConflict,
    OnConflict,
    OnTakeover,
    adoptable_equivalent,
    apply_skills_plan,
    compile_skills_plan,
    on_conflict_from_env,
    on_takeover_from_env,
    skill_id_from_target,
)
from sync import inject_kiro_arguments


class OpenSpecSkillsError(RuntimeError):
    """OpenSpec skill generation or install failed."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def openspec_command() -> Optional[Path]:
    found = shutil.which("openspec")
    return Path(found) if found else None


def render_openspec_skill_bytes(skill_dir: Path, skill_id: str) -> bytes:
    """Keep CLI-generated SKILL.md bytes; do not re-render frontmatter."""
    source = skill_dir / "SKILL.md"
    content = source.read_bytes()
    if not content.endswith(b"\n"):
        content += b"\n"
    return content


def render_openspec_kiro_skill_bytes(skill_dir: Path, skill_id: str) -> bytes:
    text = render_openspec_skill_bytes(skill_dir, skill_id).decode("utf-8")
    if not text.endswith("\n"):
        text += "\n"
    return inject_kiro_arguments(text).encode("utf-8")


def renderers_for(layout: SkillLayout):
    return (
        render_openspec_kiro_skill_bytes if layout.render == "kiro" else render_openspec_skill_bytes
    )


def generate_openspec_skills(destination: Path, *, openspec: Path) -> Path:
    """Generate generic OpenSpec skills through the Cursor adapter."""
    project = destination / "project"
    project.mkdir(parents=True)
    completed = subprocess.run(
        [str(openspec), "init", "--tools", "cursor", str(project)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "openspec init failed").strip()
        raise OpenSpecSkillsError(detail)
    generated = project / ".cursor" / "skills"
    if not generated.is_dir():
        raise OpenSpecSkillsError("openspec init --tools cursor did not create .cursor/skills")
    skills = destination / "skills"
    skills.mkdir(parents=True)
    copied = 0
    for child in sorted(generated.iterdir()):
        if not child.is_dir() or child.is_symlink():
            continue
        if not child.name.startswith("openspec-"):
            continue
        marker = child / "SKILL.md"
        if not marker.is_file() or marker.is_symlink():
            continue
        shutil.copytree(child, skills / child.name, symlinks=False)
        copied += 1
    if copied == 0:
        raise OpenSpecSkillsError("openspec init --tools cursor produced no openspec-* skills")
    return skills


def _destination_specs(
    dest_roots: Optional[Sequence[Path]],
) -> tuple[tuple[SkillLayout, Path], ...]:
    """Explicit destinations keep their layout when recognisable, else shared."""
    if dest_roots is not None:
        return tuple(
            (layout_for_target(destination) or SHARED_LAYOUT, destination.expanduser().absolute())
            for destination in dest_roots
        )
    return tuple((layout, skills_target(layout)) for layout in LAYOUTS)


def _apply_generated(
    root: Path,
    source_root: Path,
    *,
    destination: Path,
    layout: SkillLayout,
    dry_run: bool,
    on_conflict: OnConflict = "block",
    on_takeover: OnTakeover = "skip",
) -> int:
    home = home_for_target(destination)
    renderer = renderers_for(layout)
    owners = owner_prefix(layout, "openspec")
    identity = identity_prefix(layout, OPENSPEC_IDENTITY)
    plan = compile_skills_plan(
        root,
        renderer,
        home=home,
        target_root=destination,
        source_root=source_root,
        owner_prefix=owners,
        identity_prefix=identity,
        on_conflict=on_conflict,
        on_takeover=on_takeover,
    )

    adoptable = {item.target for item in adoptable_equivalent(plan)}
    blocking = [item for item in plan.conflicts if item.target not in adoptable]
    blocked = sorted({
        skill_id_from_target(item.target, destination) or "?"
        for item in blocking
    })
    write_ops = sum(
        1 for op in plan.operations
        if op.action in {"create", "update", "chmod"} or op.remediated
    )
    print(
        f"==> openspec  {layout.key}  {write_ops}↑ {len(adoptable)}adopt "
        f"{len(blocked)}✗  |  {len(plan.operations)} files"
    )
    if blocked:
        print(f"  ✗ {', '.join(blocked)}")

    if dry_run:
        return 1 if blocked else 0

    try:
        result = apply_skills_plan(plan, renderer)
    except AgentRuntimeConflict as exc:
        print(f"error: openspec skills: {exc}", file=sys.stderr)
        return 1
    skipped = result.skipped_skills
    print(
        f"  done openspec ({layout.key}): changed={result.changed} "
        f"pruned={result.pruned} unchanged={result.unchanged}"
        + (f" skipped={','.join(skipped)}" if skipped else "")
    )
    return 1 if skipped else 0


def install_openspec_skills(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
    dest_roots: Optional[Sequence[Path]] = None,
    generate=generate_openspec_skills,
    openspec: Optional[Path] = None,
    on_conflict: OnConflict | None = None,
    on_takeover: OnTakeover | None = None,
) -> int:
    """Generate OpenSpec skills with --tools agents and install them globally."""
    command = openspec if openspec is not None else openspec_command()
    if command is None:
        print("warning: openspec CLI 未安装，跳过全局 OpenSpec skills（dotf npm -i）", file=sys.stderr)
        return 0
    policy = on_conflict if on_conflict is not None else on_conflict_from_env()
    takeover = on_takeover if on_takeover is not None else on_takeover_from_env()

    # Defense in depth: reject any first-party skill named like an OpenSpec CLI
    # skill, whether catalogued or present only as a raw agents/skills/<id>/ dir.
    declared = set(first_party_skill_ids(root))
    skills_root = root / "agents" / "skills"
    if skills_root.is_dir():
        declared |= {
            path.name
            for path in skills_root.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
    overlap = sorted(item for item in declared if item.startswith("openspec-"))
    if overlap:
        print(
            "error: first-party skills overlap OpenSpec CLI skills: " + ", ".join(overlap),
            file=sys.stderr,
        )
        return 1

    destinations = (
        _destination_specs((dest_root,))
        if dest_root is not None
        else _destination_specs(dest_roots)
    )
    try:
        with tempfile.TemporaryDirectory(prefix="dotf-openspec-") as temporary:
            source_root = generate(Path(temporary), openspec=command)
            rc = 0
            for layout, destination in destinations:
                step = _apply_generated(
                    root,
                    source_root,
                    destination=destination,
                    layout=layout,
                    dry_run=dry_run,
                    on_conflict=policy,
                    on_takeover=takeover,
                )
                rc = max(rc, step)
            return rc
    except (OpenSpecSkillsError, AgentRuntimeConflict, OSError, ValueError) as exc:
        print(f"error: openspec skills: {exc}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install OpenSpec CLI skills into every managed runtime layout"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--on-conflict", choices=("block", "backup"), default=None)
    parser.add_argument("--takeover", choices=("skip", "backup"), default=None, dest="on_takeover")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()
    return install_openspec_skills(
        root,
        dry_run=args.dry_run,
        on_conflict=args.on_conflict,
        on_takeover=args.on_takeover,
    )


if __name__ == "__main__":
    raise SystemExit(main())
