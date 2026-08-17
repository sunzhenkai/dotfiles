"""taskctl 回归测试。

覆盖会造成错误写入、进度丢失或错误结案的行为，以及对既有 README 格式的向后兼容。
不测 CLI 的措辞与 JSON 排版。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "taskctl.py"
sys.path.insert(0, str(SCRIPT.parent))

import taskctl  # noqa: E402


# --------------------------------------------------------------------------- #
# 夹具
# --------------------------------------------------------------------------- #


def run(root: Path, *args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, payload


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def make_repo(path: Path, *, with_remote: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "test")
    git(path, "commit", "-q", "--allow-empty", "-m", "init")
    git(path, "branch", "-M", "main")
    if with_remote:
        bare = path.parent / f"{path.name}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        git(path, "remote", "add", "origin", str(bare))
        git(path, "push", "-q", "origin", "main")
    return path


def write_change(root: Path, name: str, items: list[str], *, done: int = 0) -> Path:
    change = root / "openspec" / "changes" / name
    change.mkdir(parents=True, exist_ok=True)
    lines = ["# Tasks", ""]
    for index, text in enumerate(items):
        lines.append(f"- [{'x' if index < done else ' '}] {text}")
    (change / "tasks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return change


def archive_change(root: Path, name: str, on: str = "2026-01-01") -> Path:
    src = root / "openspec" / "changes" / name
    dest = root / "openspec" / "changes" / "archive" / f"{on}-{name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    return dest


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "tasks").mkdir(parents=True)
    return root


def readme_of(root: Path, task_id: str) -> Path:
    matches = list((root / "tasks").glob(f"*/{task_id}-*/README.md"))
    assert len(matches) == 1, matches
    return matches[0]


def fill_readme(
    path: Path,
    *,
    scope: list[tuple[str, str]],
    changes: list[str] | None = None,
    acceptance: list[str] | None = None,
) -> None:
    """把骨架的占位行换成真实表格；scope 为 (相对路径, 角色) 列表。"""
    text = path.read_text(encoding="utf-8")
    rows = "\n".join(f"| 仓库 {p} | `{p}` | {role} | |" for p, role in scope)
    text = text.replace("| （待补） | | 必须 | |", rows)
    if changes:
        change_rows = "\n".join(
            f"| `{c}` | `openspec/changes/{c}/` | `.` | |" for c in changes
        )
        text = text.replace("| — | | | （尚无） |", change_rows)
    if acceptance is not None:
        text = text.replace("- [ ] （待补）", "\n".join(f"- [ ] {a}" for a in acceptance))
    path.write_text(text, encoding="utf-8")


def new_task(root: Path, slug: str = "demo", title: str = "示例任务") -> str:
    code, payload = run(root, "new", "--title", title, "--slug", slug)
    assert code == 0, payload
    return payload["task"]["id"]


# --------------------------------------------------------------------------- #
# 身份与索引
# --------------------------------------------------------------------------- #


def test_ids_are_sequential_and_never_reused(workspace: Path) -> None:
    assert new_task(workspace, "first") == "T0001"
    assert new_task(workspace, "second") == "T0002"

    fill_readme(readme_of(workspace, "T0001"), scope=[], acceptance=[])
    path = readme_of(workspace, "T0001")
    path.write_text(path.read_text().replace("- [ ] ", "- [x] "), encoding="utf-8")
    code, _ = run(workspace, "archive", "T0001")
    assert code == 0

    # 归档后 ID 仍不回收，避免历史引用指向另一个任务。
    assert new_task(workspace, "third") == "T0003"


def test_duplicate_active_slug_is_rejected(workspace: Path) -> None:
    new_task(workspace, "same-slug")
    code, payload = run(workspace, "new", "--title", "又一个", "--slug", "same-slug")
    assert code == 1
    assert payload["reason"] == "duplicate_slug"


@pytest.mark.parametrize("slug", ["Bad_Slug", "空格 slug", "trailing-", "双--连字符"])
def test_invalid_slug_is_rejected(workspace: Path, slug: str) -> None:
    code, payload = run(workspace, "new", "--title", "t", "--slug", slug)
    assert code == 1
    assert payload["reason"] == "invalid_slug"


def test_index_is_derived_and_repairs_manual_edits(workspace: Path) -> None:
    new_task(workspace, "alpha")
    index = workspace / "tasks" / "INDEX.md"
    assert "T0001" in index.read_text()

    index.write_text("# 手改坏了\n", encoding="utf-8")
    code, payload = run(workspace, "sync-index")
    assert code == 0
    assert payload["index"]["active"] == 1
    assert "T0001" in index.read_text()


def test_index_has_no_next_id_state(workspace: Path) -> None:
    """ID 由目录扫描分配，INDEX 不再是第二份真相源。"""
    new_task(workspace, "alpha")
    assert "next_id" not in (workspace / "tasks" / "INDEX.md").read_text()


def test_duplicate_task_id_on_disk_fails_closed(workspace: Path) -> None:
    new_task(workspace, "alpha")
    clone = workspace / "tasks" / "2020-01-01" / "T0001-conflict"
    clone.mkdir(parents=True)
    (clone / "README.md").write_text("# 冲突\n", encoding="utf-8")
    code, payload = run(workspace, "list")
    assert code == 1
    assert payload["reason"] == "duplicate_id"


# --------------------------------------------------------------------------- #
# resolve
# --------------------------------------------------------------------------- #


def test_resolve_by_id(workspace: Path) -> None:
    new_task(workspace, "alpha")
    code, payload = run(workspace, "resolve", "T0001", "--command", "task-apply")
    assert code == 0
    assert payload["task"]["id"] == "T0001"
    assert payload["command"] == "task-apply"


def test_resolve_ambiguous_needs_confirm(workspace: Path) -> None:
    new_task(workspace, "alpha-one")
    new_task(workspace, "alpha-two")
    code, payload = run(workspace, "resolve", "--hint", "alpha")
    assert code == 2
    assert payload["reason"] == "ambiguous"
    assert len(payload["candidates"]) == 2


def test_resolve_without_query_needs_confirm(workspace: Path) -> None:
    new_task(workspace, "alpha")
    code, payload = run(workspace, "resolve")
    assert code == 2
    assert payload["reason"] == "no_query"


def test_resolve_unknown_query_needs_confirm(workspace: Path) -> None:
    new_task(workspace, "alpha")
    code, payload = run(workspace, "resolve", "nothing-like-this")
    assert code == 2
    assert payload["reason"] == "not_found"


def test_resolve_archived_task_reports_restore(workspace: Path) -> None:
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[], acceptance=[])
    path = readme_of(workspace, "T0001")
    path.write_text(path.read_text().replace("- [ ] ", "- [x] "), encoding="utf-8")
    assert run(workspace, "archive", "T0001")[0] == 0

    code, payload = run(workspace, "resolve", "T0001")
    assert code == 2
    assert payload["reason"] == "archived"
    assert "restore" in payload["action"]


# --------------------------------------------------------------------------- #
# status：只读、不调 git、checkbox 是唯一进度源
# --------------------------------------------------------------------------- #


def test_status_reports_checkbox_progress(workspace: Path) -> None:
    new_task(workspace, "alpha")
    write_change(workspace, "add-thing", ["一", "二", "三"], done=1)
    fill_readme(
        readme_of(workspace, "T0001"),
        scope=[("svc", "必须")],
        changes=["add-thing"],
        acceptance=["可用"],
    )
    code, payload = run(workspace, "status", "T0001")
    assert code == 0
    assert payload["progress"] == {"total": 3, "complete": 1, "remaining": 2}
    assert payload["openspec"][0]["remaining"] == ["二", "三"]
    assert payload["acceptance"]["unchecked"] == ["可用"]


def test_status_works_before_branches_are_prepared(workspace: Path) -> None:
    """查进度不过 checkout gate，也不要求仓库存在。"""
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("missing-repo", "必须")])
    code, payload = run(workspace, "status", "T0001")
    assert code == 0
    assert payload["work_context"] == []


def test_status_writes_nothing(workspace: Path) -> None:
    new_task(workspace, "alpha")
    path = readme_of(workspace, "T0001")
    before = path.read_text()
    assert run(workspace, "status", "T0001")[0] == 0
    assert path.read_text() == before


def test_missing_change_is_named_not_guessed(workspace: Path) -> None:
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[], changes=["never-created"])
    code, payload = run(workspace, "status", "T0001")
    assert code == 0
    assert payload["openspec"][0]["state"] == "missing"


def test_archived_change_progress_is_read_from_archive(workspace: Path) -> None:
    new_task(workspace, "alpha")
    write_change(workspace, "add-thing", ["一", "二"], done=2)
    fill_readme(readme_of(workspace, "T0001"), scope=[], changes=["add-thing"])
    archive_change(workspace, "add-thing")
    code, payload = run(workspace, "status", "T0001")
    assert code == 0
    report = payload["openspec"][0]
    assert report["state"] == "archived"
    assert (report["complete"], report["total"]) == (2, 2)


def test_similar_change_name_in_archive_is_not_mistaken(workspace: Path) -> None:
    """归档识别按 YYYY-MM-DD-<change> 整名匹配，同名前缀的他人归档不算数。"""
    new_task(workspace, "alpha")
    write_change(workspace, "add-thing", ["一"])
    fill_readme(readme_of(workspace, "T0001"), scope=[], changes=["add-thing"])
    archive_change(workspace, "add-thing")
    (workspace / "openspec" / "changes" / "archive" / "2026-01-01-add-thing-extended").mkdir()

    report = run(workspace, "status", "T0001")[1]["openspec"][0]
    assert report["archived_as"] == ["openspec/changes/archive/2026-01-01-add-thing"]


def test_unknown_scope_role_fails_closed(workspace: Path) -> None:
    new_task(workspace, "alpha")
    path = readme_of(workspace, "T0001")
    path.write_text(
        path.read_text().replace("| （待补） | | 必须 | |", "| 仓 | `svc` | 也许 | |"),
        encoding="utf-8",
    )
    code, payload = run(workspace, "status", "T0001")
    assert code == 1
    assert payload["reason"] == "malformed_scope"


# --------------------------------------------------------------------------- #
# set-status
# --------------------------------------------------------------------------- #


def test_set_status_updates_readme_and_changelog(workspace: Path) -> None:
    new_task(workspace, "alpha")
    code, payload = run(workspace, "set-status", "T0001", "proposed")
    assert code == 0
    assert payload["task"]["status"] == "proposed"
    text = readme_of(workspace, "T0001").read_text()
    assert "**status：** proposed" in text
    assert "draft → proposed" in text


def test_set_status_rejects_unknown_value(workspace: Path) -> None:
    new_task(workspace, "alpha")
    code, payload = run(workspace, "set-status", "T0001", "almost-done")
    assert code == 1
    assert payload["reason"] == "invalid_status"


def test_set_status_cannot_archive(workspace: Path) -> None:
    """归档必须走 archive，以便同时校验 checkbox、验收与交付仓状态。"""
    new_task(workspace, "alpha")
    code, payload = run(workspace, "set-status", "T0001", "archived")
    assert code == 1
    assert payload["reason"] == "usage"


# --------------------------------------------------------------------------- #
# prepare-branches
# --------------------------------------------------------------------------- #


def test_prepare_branches_touches_only_must_repos(workspace: Path) -> None:
    must = make_repo(workspace / "svc-must")
    suggested = make_repo(workspace / "svc-suggested")
    excluded = make_repo(workspace / "svc-excluded")
    new_task(workspace, "alpha")
    fill_readme(
        readme_of(workspace, "T0001"),
        scope=[("svc-must", "必须"), ("svc-suggested", "建议"), ("svc-excluded", "排除")],
    )
    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 0
    assert [row["repo"] for row in payload["prepared"]] == ["svc-must"]
    assert taskctl.current_branch(must) == "feat-alpha"
    assert taskctl.current_branch(suggested) == "main"
    assert taskctl.current_branch(excluded) == "main"


def test_prepare_branches_blocks_dirty_and_keeps_worktree_intact(workspace: Path) -> None:
    repo = make_repo(workspace / "svc")
    (repo / "wip.txt").write_text("uncommitted", encoding="utf-8")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])

    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 2
    assert payload["blocked"][0]["reason"] == "dirty"
    # fail closed：既不切分支，也不动用户的未提交改动。
    assert taskctl.current_branch(repo) == "main"
    assert (repo / "wip.txt").read_text() == "uncommitted"


def test_prepare_branches_blocks_unreachable_origin(workspace: Path) -> None:
    repo = make_repo(workspace / "svc")
    git(repo, "remote", "set-url", "origin", str(workspace / "gone.git"))
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])

    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 2
    assert payload["blocked"][0]["reason"] == "fetch_failed"
    assert taskctl.current_branch(repo) == "main"


def test_prepare_branches_keeps_ready_repos_when_another_blocks(workspace: Path) -> None:
    ready = make_repo(workspace / "svc-ready")
    blocked = make_repo(workspace / "svc-blocked")
    (blocked / "wip.txt").write_text("x", encoding="utf-8")
    new_task(workspace, "alpha")
    fill_readme(
        readme_of(workspace, "T0001"),
        scope=[("svc-ready", "必须"), ("svc-blocked", "必须")],
    )
    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 2
    assert [row["repo"] for row in payload["prepared"]] == ["svc-ready"]
    assert taskctl.current_branch(ready) == "feat-alpha"
    # 已准备好的仓记录下来，重试不必从头再来。
    assert "svc-ready" in readme_of(workspace, "T0001").read_text()


def test_prepare_branches_reuses_current_task_branch_with_wip(workspace: Path) -> None:
    repo = make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])
    assert run(workspace, "prepare-branches", "T0001")[0] == 0

    (repo / "wip.txt").write_text("续作中", encoding="utf-8")
    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 0
    assert payload["prepared"][0]["action"] == "reused"
    assert (repo / "wip.txt").read_text() == "续作中"


def test_prepare_branches_is_idempotent_in_readme(workspace: Path) -> None:
    make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])
    for _ in range(3):
        assert run(workspace, "prepare-branches", "T0001")[0] == 0
    text = readme_of(workspace, "T0001").read_text()
    assert text.count("| `svc` | `feat-alpha` | `main` |") == 1
    assert "\n\n\n" not in text


def test_prepare_branches_promotes_status_to_in_progress(workspace: Path) -> None:
    make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])
    assert run(workspace, "set-status", "T0001", "proposed")[0] == 0
    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 0
    assert payload["task"]["status"] == "in_progress"


def test_prepare_branches_requires_a_must_repo(workspace: Path) -> None:
    new_task(workspace, "alpha")
    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 1
    assert payload["reason"] == "no_must_repo"


def test_prepare_branches_rejects_non_git_path(workspace: Path) -> None:
    (workspace / "not-a-repo").mkdir()
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("not-a-repo", "必须")])
    code, payload = run(workspace, "prepare-branches", "T0001")
    assert code == 2
    assert payload["blocked"][0]["reason"] == "not_git_root"


def test_prepare_branches_honours_prefix(workspace: Path) -> None:
    repo = make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])
    assert run(workspace, "prepare-branches", "T0001", "--prefix", "fix")[0] == 0
    assert taskctl.current_branch(repo) == "fix-alpha"


def test_prepare_branches_dry_run_writes_nothing(workspace: Path) -> None:
    make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")])
    before = readme_of(workspace, "T0001").read_text()
    assert run(workspace, "prepare-branches", "T0001", "--dry-run")[0] == 0
    assert readme_of(workspace, "T0001").read_text() == before


# --------------------------------------------------------------------------- #
# archive
# --------------------------------------------------------------------------- #


@pytest.fixture()
def ready_to_archive(workspace: Path) -> Path:
    """一个 checkbox 与验收都已完成、交付仓 clean 的任务。"""
    make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    write_change(workspace, "add-thing", ["一", "二"], done=2)
    fill_readme(
        readme_of(workspace, "T0001"),
        scope=[("svc", "必须")],
        changes=["add-thing"],
        acceptance=["可用"],
    )
    assert run(workspace, "prepare-branches", "T0001")[0] == 0
    path = readme_of(workspace, "T0001")
    path.write_text(path.read_text().replace("- [ ] 可用", "- [x] 可用"), encoding="utf-8")
    return workspace


def gate_names(payload: dict) -> set[str]:
    return {item["gate"] for item in payload["confirmations"]}


def test_archive_confirms_remaining_checkboxes(workspace: Path) -> None:
    new_task(workspace, "alpha")
    write_change(workspace, "add-thing", ["一", "二"], done=1)
    fill_readme(
        readme_of(workspace, "T0001"), scope=[], changes=["add-thing"], acceptance=[]
    )
    code, payload = run(workspace, "archive", "T0001", "--dry-run")
    assert code == 2
    assert "openspec_remaining" in gate_names(payload)
    confirm = next(c for c in payload["confirmations"] if c["gate"] == "openspec_remaining")
    assert confirm["exact_action"] == "--allow-remaining"
    assert confirm["affected"][0]["remaining"] == ["二"]


def test_archive_confirms_unchecked_acceptance(workspace: Path) -> None:
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[], acceptance=["尚未达成"])
    code, payload = run(workspace, "archive", "T0001", "--dry-run")
    assert code == 2
    assert "unchecked_acceptance" in gate_names(payload)


def test_archive_confirms_dirty_delivery_per_repo(ready_to_archive: Path) -> None:
    (ready_to_archive / "svc" / "wip.txt").write_text("x", encoding="utf-8")
    code, payload = run(ready_to_archive, "archive", "T0001", "--dry-run")
    assert code == 2
    confirm = next(c for c in payload["confirmations"] if c["gate"] == "dirty_delivery")
    assert confirm["exact_action"] == "--allow-dirty svc"


def test_archive_override_only_clears_its_own_gate(workspace: Path) -> None:
    new_task(workspace, "alpha")
    write_change(workspace, "add-thing", ["一"], done=0)
    fill_readme(
        readme_of(workspace, "T0001"),
        scope=[],
        changes=["add-thing"],
        acceptance=["尚未达成"],
    )
    code, payload = run(workspace, "archive", "T0001", "--dry-run", "--allow-remaining")
    assert code == 2
    assert gate_names(payload) == {"unchecked_acceptance"}


def test_archive_refuses_finalize_while_change_active(ready_to_archive: Path) -> None:
    code, payload = run(ready_to_archive, "archive", "T0001")
    assert code == 1
    assert payload["reason"] == "openspec_not_archived"
    # task 保持 active，重试不需要先 restore。
    assert list((ready_to_archive / "tasks").glob("2*/T0001-alpha"))
    assert run(ready_to_archive, "resolve", "T0001")[0] == 0


def test_archive_dry_run_points_at_openspec_archive(ready_to_archive: Path) -> None:
    code, payload = run(ready_to_archive, "archive", "T0001", "--dry-run")
    assert code == 0
    assert payload["pending_openspec_archive"] == ["add-thing"]
    assert "openspec CLI" in payload["next_action"]
    assert "add-thing" in payload["next_action"]


def test_archive_finalizes_and_records_delivery(ready_to_archive: Path) -> None:
    archive_change(ready_to_archive, "add-thing")
    code, payload = run(ready_to_archive, "archive", "T0001")
    assert code == 0

    dest = ready_to_archive / payload["archived_path"]
    assert dest.is_dir()
    assert not list((ready_to_archive / "tasks").glob("2*/T0001-*"))
    assert "**status：** archived" in (dest / "README.md").read_text()

    changes = (dest / "changes.md").read_text()
    assert "`svc`" in changes and "feat-alpha" in changes
    assert "add-thing" in changes


def test_archive_audits_overrides(workspace: Path) -> None:
    make_repo(workspace / "svc")
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[("svc", "必须")], acceptance=["未达成"])
    assert run(workspace, "prepare-branches", "T0001")[0] == 0
    code, payload = run(workspace, "archive", "T0001", "--allow-unchecked-acceptance")
    assert code == 0
    assert payload["overrides"] == ["allow_unchecked_acceptance"]
    changes = (workspace / payload["archived_path"] / "changes.md").read_text()
    assert "allow_unchecked_acceptance" in changes


def test_archive_prunes_empty_date_directory(ready_to_archive: Path) -> None:
    archive_change(ready_to_archive, "add-thing")
    assert run(ready_to_archive, "archive", "T0001")[0] == 0
    leftovers = [p.name for p in (ready_to_archive / "tasks").iterdir() if p.is_dir()]
    assert leftovers == ["archive"]


def test_archive_missing_change_is_a_hard_error(workspace: Path) -> None:
    new_task(workspace, "alpha")
    fill_readme(readme_of(workspace, "T0001"), scope=[], changes=["never-created"])
    code, payload = run(workspace, "archive", "T0001", "--dry-run")
    assert code == 1
    assert payload["reason"] == "missing_openspec"


# --------------------------------------------------------------------------- #
# restore
# --------------------------------------------------------------------------- #


def test_restore_brings_task_back_as_active(ready_to_archive: Path) -> None:
    archive_change(ready_to_archive, "add-thing")
    assert run(ready_to_archive, "archive", "T0001")[0] == 0

    code, payload = run(ready_to_archive, "restore", "T0001")
    assert code == 0
    assert payload["task"]["status"] == "in_progress"
    assert run(ready_to_archive, "resolve", "T0001")[0] == 0


# --------------------------------------------------------------------------- #
# 工作区笔记
# --------------------------------------------------------------------------- #


def test_notes_roundtrip(workspace: Path) -> None:
    code, payload = run(workspace, "notes")
    assert code == 0 and payload["exists"] is False

    assert run(workspace, "notes", "--set-section", "默认涉及面", "--body", "只改 svc")[0] == 0
    code, payload = run(workspace, "notes")
    assert payload["sections"]["默认涉及面"] == "只改 svc"

    assert run(workspace, "notes", "--set-section", "默认涉及面", "--body", "改 svc 与 web")[0] == 0
    assert run(workspace, "notes")[1]["sections"]["默认涉及面"] == "改 svc 与 web"


def test_notes_reach_commands_as_hard_constraints(workspace: Path) -> None:
    assert run(workspace, "notes", "--set-section", "规格", "--body", "禁止提交密钥")[0] == 0
    new_task(workspace, "alpha")
    assert run(workspace, "resolve", "T0001")[1]["workflow_notes"]["sections"]["规格"] == "禁止提交密钥"


# --------------------------------------------------------------------------- #
# 不再维护第二份进度状态
# --------------------------------------------------------------------------- #


def test_no_parallel_progress_state_files(ready_to_archive: Path) -> None:
    archive_change(ready_to_archive, "add-thing")
    assert run(ready_to_archive, "archive", "T0001")[0] == 0
    stale = [
        path.name
        for path in (ready_to_archive / "tasks").rglob("*")
        if path.name in {"progress.md", ".task-apply-state.json"}
    ]
    assert stale == []


def test_public_command_surface_is_small() -> None:
    assert set(taskctl.COMMANDS) == {
        "new",
        "list",
        "resolve",
        "status",
        "set-status",
        "prepare-branches",
        "archive",
        "restore",
        "notes",
        "sync-index",
    }


# --------------------------------------------------------------------------- #
# --root 解析
# --------------------------------------------------------------------------- #


def test_root_accepted_before_and_after_subcommand(workspace: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "new", "--root", str(workspace), "--title", "t", "--slug", "s"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["task"]["id"] == "T0001"


def test_conflicting_root_values_are_rejected(workspace: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--root", str(workspace),
            "list", "--root", str(workspace / "other"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["reason"] == "usage"


def test_workspace_is_discovered_from_cwd(workspace: Path) -> None:
    new_task(workspace, "alpha")
    nested = workspace / "deep" / "nested"
    nested.mkdir(parents=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "list"],
        cwd=nested,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["active"][0]["id"] == "T0001"


# --------------------------------------------------------------------------- #
# 解析器单元测试：向后兼容既有 README 表格
# --------------------------------------------------------------------------- #


LEGACY_README = """# 旧格式任务

**id：** T0042
**status：** in_progress
**slug：** legacy-task
**创建时间：** 2026-06-16

## 需求说明

### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| Workflow BFF | `codes/a` | 必须 |
| 参考能力 | `codes/b` | 建议 |

### 关联 OpenSpec

| change | 路径 | 仓库 | store | 说明 |
|--------|------|------|-------|------|
| `establish-thing` | `openspec/changes/establish-thing/` | `.` |  | foundation |

## 方案笔记（2026-08-15 task-explore）

### 1. 已有基础

正文若干。

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| codes/a | `codes/a` | `codes/a` | 否 | `feat-legacy-task` | `main` |

## 验收标准

- [x] 已达成
- [ ] 未达成

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-06-16 | 创建任务 |
"""


def test_legacy_scope_table_without_note_column() -> None:
    scope = taskctl.parse_scope(LEGACY_README)
    assert [(row["path"], row["role"]) for row in scope] == [
        ("codes/a", "must"),
        ("codes/b", "suggested"),
    ]


def test_legacy_openspec_table_ignores_store_column() -> None:
    entries = taskctl.parse_openspec(LEGACY_README)
    assert entries == [
        {
            "change": "establish-thing",
            "path": "openspec/changes/establish-thing/",
            "repo": ".",
            "note": "foundation",
        }
    ]


def test_legacy_work_context_columns_are_read_by_name() -> None:
    rows = taskctl.parse_work_context(LEGACY_README)
    assert rows == [{"repo": "codes/a", "branch": "feat-legacy-task", "base": "main"}]


def test_legacy_acceptance_and_frontmatter() -> None:
    assert taskctl.frontmatter_field(LEGACY_README, "id") == "T0042"
    acceptance = taskctl.parse_acceptance(LEGACY_README)
    assert [item["done"] for item in acceptance] == [True, False]


def test_heading_with_suffix_is_matched() -> None:
    body = taskctl.section_body(LEGACY_README, "方案笔记")
    assert "已有基础" in body
    # 同级标题终止小节，不吞掉后面的工作上下文。
    assert "工作上下文" not in body


def test_replace_section_does_not_accumulate_blank_lines() -> None:
    text = LEGACY_README
    for _ in range(3):
        text = taskctl.replace_section(text, "工作上下文", "| 仓库 | 分支 | 基线 |\n|--|--|--|")
    assert "\n\n\n" not in text
    assert taskctl.section_body(text, "验收标准").strip().startswith("- [x]")


def test_set_frontmatter_field_touches_one_line() -> None:
    updated = taskctl.set_frontmatter_field(LEGACY_README, "status", "archived")
    assert "**status：** archived" in updated
    assert "**slug：** legacy-task" in updated
    assert updated.count("**status：**") == 1


def test_placeholder_rows_are_not_data() -> None:
    scaffold = taskctl.scaffold_readme(
        task_id="T0001", slug="alpha", title="示例", created="2026-08-17"
    )
    assert taskctl.parse_scope(scaffold) == []
    assert taskctl.parse_openspec(scaffold) == []
    assert taskctl.parse_work_context(scaffold) == []
