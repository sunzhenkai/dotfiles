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
from managed_runtime import AgentRuntimeConflict, apply_skills_plan, compile_skills_plan
from sync import inject_kiro_arguments, kiro_skills_target, skills_target

OPENSPEC_OWNER = "agents:openspec:"
KIRO_OPENSPEC_OWNER = "agents:kiro-openspec:"
IDENTITY_PREFIX = "openspec-cli"
KIRO_IDENTITY_PREFIX = "openspec-cli:kiro"
ADOPT_REASON = "target exists without agents ownership"


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


def generate_openspec_skills(destination: Path, *, openspec: Path) -> Path:
    """Run `openspec init --tools agents` in an isolated project and copy skills."""
    project = destination / "project"
    project.mkdir(parents=True)
    completed = subprocess.run(
        [str(openspec), "init", "--tools", "agents", "--no-animation", str(project)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "openspec init failed").strip()
        raise OpenSpecSkillsError(detail)
    generated = project / ".agents" / "skills"
    if not generated.is_dir():
        raise OpenSpecSkillsError("openspec init --tools agents did not create .agents/skills")
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
        raise OpenSpecSkillsError("openspec init --tools agents produced no openspec-* skills")
    return skills


def _home_for_target(destination: Path) -> Path:
    destination = destination.expanduser().absolute()
    if destination.name == "skills" and destination.parent.name == ".agents":
        return destination.parent.parent
    if destination.name == "skills" and destination.parent.name == ".kiro":
        return destination.parent.parent
    return Path.home().expanduser().absolute()


def _destination_specs(
    dest_roots: Optional[Sequence[Path]],
) -> tuple[tuple[Path, str, str], ...]:
    if dest_roots is not None:
        result = []
        for destination in dest_roots:
            destination = destination.expanduser().absolute()
            if destination.parent.name == ".kiro":
                result.append((destination, KIRO_OPENSPEC_OWNER, "kiro"))
            else:
                result.append((destination, OPENSPEC_OWNER, "shared"))
        return tuple(result)
    return (
        (skills_target(), OPENSPEC_OWNER, "shared"),
        (kiro_skills_target(), KIRO_OPENSPEC_OWNER, "kiro"),
    )


def _adoptable_equivalent(plan) -> list:
    adoptable = []
    for operation in plan.conflicts:
        if operation.conflict != ADOPT_REASON or operation.expected is None:
            continue
        target = Path(operation.target)
        if not target.is_file() or target.is_symlink():
            continue
        if target.read_bytes() == operation.expected.content:
            adoptable.append(operation)
    return adoptable


def _apply_generated(
    root: Path,
    source_root: Path,
    *,
    destination: Path,
    owner_prefix: str,
    identity_prefix: str,
    layout: str,
    dry_run: bool,
) -> int:
    home = _home_for_target(destination)
    renderer = render_openspec_kiro_skill_bytes if layout == "kiro" else render_openspec_skill_bytes
    print(f"==> openspec skills ({layout}) → {destination}")
    plan = compile_skills_plan(
        root,
        renderer,
        home=home,
        target_root=destination,
        source_root=source_root,
        owner_prefix=owner_prefix,
        identity_prefix=identity_prefix,
    )
    released: list[tuple[Path, bytes]] = []
    if not dry_run:
        for operation in _adoptable_equivalent(plan):
            target = Path(operation.target)
            released.append((target, operation.expected.content))
            target.unlink()
        if released:
            plan = compile_skills_plan(
                root,
                renderer,
                home=home,
                target_root=destination,
                source_root=source_root,
                owner_prefix=owner_prefix,
                identity_prefix=identity_prefix,
            )

    markers = {
        "none": "=",
        "create": "+",
        "update": "+",
        "chmod": "~",
        "prune": "-",
        "block": "!",
    }
    for operation in plan.operations:
        marker = markers[operation.action]
        suffix = ""
        if dry_run and operation.conflict == ADOPT_REASON and operation.expected is not None:
            target = Path(operation.target)
            if target.is_file() and target.read_bytes() == operation.expected.content:
                marker = "+"
                suffix = " (adopt equivalent)"
        print(f"  {marker} {operation.target}{suffix}")
        if operation.conflict and suffix == "":
            print(f"    conflict: {operation.conflict}")

    if dry_run:
        changed = sum(item.action in {"create", "update", "chmod"} for item in plan.operations)
        pruned = sum(item.action == "prune" for item in plan.operations)
        unchanged = sum(item.action == "none" for item in plan.operations)
        adoptable = len(_adoptable_equivalent(plan))
        conflicts = len(plan.conflicts) - adoptable
        print(
            f"  done openspec ({layout}, plan): changed={changed} pruned={pruned} "
            f"unchanged={unchanged} adopt={adoptable} conflicts={conflicts}"
        )
        return 1 if conflicts else 0

    try:
        result = apply_skills_plan(plan, renderer)
    except AgentRuntimeConflict as exc:
        for target, content in released:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        print(f"error: openspec skills: {exc}", file=sys.stderr)
        return 1
    print(
        f"  done openspec ({layout}): changed={result.changed} "
        f"pruned={result.pruned} unchanged={result.unchanged}"
    )
    return 0


def install_openspec_skills(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
    dest_roots: Optional[Sequence[Path]] = None,
    generate=generate_openspec_skills,
    openspec: Optional[Path] = None,
) -> int:
    """Generate OpenSpec skills with --tools agents and install them globally."""
    command = openspec if openspec is not None else openspec_command()
    if command is None:
        print("warning: openspec CLI 未安装，跳过全局 OpenSpec skills（dotf npm -i）", file=sys.stderr)
        return 0

    overlap = [item for item in first_party_skill_ids(root) if item.startswith("openspec-")]
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
            for destination, owner_prefix, layout in destinations:
                identity = KIRO_IDENTITY_PREFIX if layout == "kiro" else IDENTITY_PREFIX
                step = _apply_generated(
                    root,
                    source_root,
                    destination=destination,
                    owner_prefix=owner_prefix,
                    identity_prefix=identity,
                    layout=layout,
                    dry_run=dry_run,
                )
                rc = max(rc, step)
            return rc
    except (OpenSpecSkillsError, AgentRuntimeConflict, OSError, ValueError) as exc:
        print(f"error: openspec skills: {exc}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install OpenSpec CLI skills into ~/.agents/skills (and Kiro)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()
    return install_openspec_skills(root, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
