"""sync.py 分发 skill 到各 layout：references/scripts 原样拷贝。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "agents"))

from layouts import CLAUDE, KIRO, SHARED, skills_target  # noqa: E402
from sync import validate_output  # noqa: E402

RUNTIME_YAML = (
    "version: 1\nskills:\n  files:\n    - SKILL.md\n  sidecars:\n    - references\n    - scripts\n"
    "  excluded:\n    - patches\n    - evals\n    - experience\n    - evolutions\n    - authoring\n"
)
CATALOG_YAML = (
    "version: 3\nlock: skills.lock.yaml\ngroups:\n"
    "  dotfiles:\n    type: first-party\n    skills:\n      - demo-skill\n"
)
LOCK_YAML = "schema_version: 1\nkind: third-party-skills-lock\nskills: []\n"


@pytest.fixture
def first_party_repo(tmp_path: Path) -> Path:
    """first-party 集合当前为空：分发语义用 DOTF 沙箱仓验证。"""
    repo = tmp_path / "repo"
    skill = repo / "agents" / "skills" / "demo-skill"
    (skill / "references").mkdir(parents=True)
    (skill / "scripts").mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: sandbox fixture\n---\n\n"
        "Use {{slash:demo-skill}} to run.\n",
        encoding="utf-8",
    )
    (skill / "references" / "ingest.md").write_bytes(b"ingest-bytes\n")
    (skill / "scripts" / "specctl.py").write_bytes(b"print('specctl')\n")
    agents = repo / "agents"
    (agents / "skills.yaml").write_text(CATALOG_YAML, encoding="utf-8")
    (agents / "skills.lock.yaml").write_text(LOCK_YAML, encoding="utf-8")
    (agents / "runtime.yaml").write_text(RUNTIME_YAML, encoding="utf-8")
    return repo


def _run_sync(
    tmp_home: Path,
    root: Path,
    *,
    kiro_home: str | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["XDG_STATE_HOME"] = str(tmp_home / ".local" / "state")
    if kiro_home is not None:
        env["KIRO_HOME"] = kiro_home
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "agents" / "sync.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def test_sync_copies_skill_references(tmp_path: Path, first_party_repo: Path) -> None:
    r = _run_sync(tmp_path, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    src = first_party_repo / "agents" / "skills" / "demo-skill" / "references" / "ingest.md"
    dest = tmp_path / ".agents" / "skills" / "demo-skill" / "references" / "ingest.md"
    assert dest.is_file(), f"references 未分发: {dest}\n{r.stdout}"
    # 原样拷贝：字节一致（不做 frontmatter 渲染 / slash 替换）
    assert dest.read_bytes() == src.read_bytes()


def test_sync_references_idempotent(tmp_path: Path, first_party_repo: Path) -> None:
    r1 = _run_sync(tmp_path, first_party_repo)
    assert r1.returncode == 0, r1.stderr + r1.stdout
    r2 = _run_sync(tmp_path, first_party_repo)
    assert r2.returncode == 0, r2.stderr + r2.stdout
    # 第二次运行不再写入（全部 skip）
    assert "references/ingest.md" not in "\n".join(
        line for line in r2.stdout.splitlines() if line.startswith("  +")
    )


def test_sync_copies_skill_scripts(tmp_path: Path, first_party_repo: Path) -> None:
    r = _run_sync(tmp_path, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    src = first_party_repo / "agents" / "skills" / "demo-skill" / "scripts" / "specctl.py"
    dest = tmp_path / ".agents" / "skills" / "demo-skill" / "scripts" / "specctl.py"
    assert dest.is_file(), f"scripts 未分发: {dest}\n{r.stdout}"
    assert dest.read_bytes() == src.read_bytes()


def test_sync_renders_slash_placeholders(tmp_path: Path, first_party_repo: Path) -> None:
    r = _run_sync(tmp_path, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    # {{slash:xxx}} 统一渲染为 /xxx；输出不得残留占位符
    skill = tmp_path / ".agents" / "skills" / "demo-skill" / "SKILL.md"
    assert skill.is_file(), f"skill 未同步: {skill}\n{r.stdout}"
    content = skill.read_text()
    assert "{{slash:" not in content
    assert "/demo-skill" in content


def test_validate_output_allows_literal_object_braces() -> None:
    # 第三方/前端 skill 正文可能包含 JavaScript 对象示例（如 `value={{...}}`），
    # 不是 sync 的 slash 模板占位符。
    validate_output(Path("SKILL.md"), "const value = {{ once: true, amount: 0.3 }};")


def test_sync_also_targets_kiro_cli_skills(
    tmp_path: Path, first_party_repo: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    r = _run_sync(home, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    shared = home / ".agents" / "skills" / "demo-skill" / "SKILL.md"
    kiro = home / ".kiro" / "skills" / "demo-skill" / "SKILL.md"
    assert shared.is_file()
    assert kiro.is_file(), f"Kiro skills 未分发: {kiro}\n{r.stdout}"
    assert shared.read_text().rstrip().endswith("$ARGUMENTS") is False
    assert kiro.read_text().rstrip().endswith("$ARGUMENTS")
    kiro_reference = home / ".kiro" / "skills" / "demo-skill" / "references" / "ingest.md"
    source_reference = (
        first_party_repo / "agents" / "skills" / "demo-skill" / "references" / "ingest.md"
    )
    assert kiro_reference.read_bytes() == source_reference.read_bytes()


def test_sync_kiro_cli_respects_kiro_home(
    tmp_path: Path, first_party_repo: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    kiro_home = home / "kiro-root"
    r = _run_sync(home, first_party_repo, kiro_home=str(kiro_home))
    assert r.returncode == 0, r.stderr + r.stdout
    assert (kiro_home / "skills" / "demo-skill" / "SKILL.md").is_file()


def test_explicit_home_still_defaults_to_kiro_directory() -> None:
    home = Path("/tmp/dotf-test-home")
    assert skills_target(KIRO, home) == home / ".kiro" / "skills"


def test_claude_target_loads_skills_code_writes_verbatim(
    tmp_path: Path, first_party_repo: Path
) -> None:
    # Claude Code reads personal skills from ~/.claude/skills/<id>/SKILL.md and
    # consumes $ARGUMENTS itself, so this layout must not inject the Kiro marker.
    home = tmp_path / "home"
    home.mkdir()
    r = _run_sync(home, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    claude = home / ".claude" / "skills" / "demo-skill" / "SKILL.md"
    assert claude.is_file(), f"Claude skills 未分发: {claude}\n{r.stdout}"
    assert claude.read_text().rstrip().endswith("$ARGUMENTS") is False
    assert "{{slash:" not in claude.read_text()
    assert skills_target(CLAUDE, home) == home / ".claude" / "skills"


def test_every_layout_receives_identical_first_party_files(
    tmp_path: Path, first_party_repo: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    r = _run_sync(home, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    relative = Path("demo-skill") / "references" / "ingest.md"
    shared = skills_target(SHARED, home) / relative
    kiro = skills_target(KIRO, home) / relative
    claude = skills_target(CLAUDE, home) / relative
    assert shared.read_bytes() == kiro.read_bytes() == claude.read_bytes()


def test_sync_installs_no_taskctl_shim(tmp_path: Path, first_party_repo: Path) -> None:
    r = _run_sync(tmp_path, first_party_repo)
    assert r.returncode == 0, r.stderr + r.stdout
    shim = tmp_path / ".local" / "bin" / "taskctl"
    assert not shim.exists(), f"不应再安装 taskctl shim: {shim}"
