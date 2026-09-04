"""Canonical Agent doctor state, boundary, security, and renderer tests."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

import doctor  # noqa: E402
from common import Catalog  # noqa: E402


def _report() -> doctor.DoctorReport:
    return doctor.DoctorReport("research", None, "low")


def _messages(report: doctor.DoctorReport) -> str:
    return "\n".join(f"{item.id} {item.status} {item.message} {item.hint}" for item in report.items)


def test_skills_plan_reports_all_states_managed_counts_and_safe_conflict_hint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prior = object()
    operations = (
        SimpleNamespace(prior=prior, state="unchanged", action="none", actual_state="present", conflict=None, target="/home/managed"),
        SimpleNamespace(prior=None, state="create", action="create", actual_state="missing", conflict=None, target="/home/missing"),
        SimpleNamespace(prior=prior, state="update", action="update", actual_state="present", conflict=None, target="/home/changed"),
        SimpleNamespace(prior=prior, state="prune", action="prune", actual_state="present", conflict=None, target="/home/stale"),
        SimpleNamespace(prior=prior, state="permission", action="chmod", actual_state="present", conflict=None, target="/home/mode"),
        SimpleNamespace(prior=None, state="conflict", action="block", actual_state="present", conflict="target exists without agents ownership", target="/home/unowned"),
        SimpleNamespace(prior=prior, state="conflict", action="block", actual_state="present", conflict="owned target was modified locally", target="/home/local"),
        SimpleNamespace(prior=prior, state="conflict", action="block", actual_state="unsafe", conflict="target path contains a symlink or unsafe type", target="/home/link"),
    )
    plan = SimpleNamespace(manifest_status="ok", state_home=str(tmp_path), operations=operations)
    monkeypatch.setattr(doctor, "compile_skills_plan", lambda *args, **kwargs: plan)
    report = _report()

    doctor.check_skills_plan(tmp_path, report, home=tmp_path)

    text = _messages(report)
    for state in ("missing", "changed", "stale", "unowned", "conflict", "permission", "link-boundary"):
        assert state in text
    summary = next(item for item in report.items if item.id == "sync-plan")
    assert "managed=6" in summary.message
    local = next(item for item in report.items if "/home/local" in item.message)
    assert local.status == doctor.STATUS_FAIL
    assert "禁止静默覆盖" in local.hint


def test_mcp_plan_reports_all_states_malformed_counts_and_pinned_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    entries = (
        SimpleNamespace(ownership="owned", state="create", conflict=None, server_id="missing"),
        SimpleNamespace(ownership="owned", state="update", conflict=None, server_id="changed"),
        SimpleNamespace(ownership="owned", state="prune", conflict=None, server_id="stale"),
        SimpleNamespace(ownership="unowned", state="unchanged", conflict=None, server_id="private"),
        SimpleNamespace(ownership="owned", state="conflict", conflict="owned MCP entry was modified locally", server_id="local"),
    )
    normal = SimpleNamespace(
        adapter="cursor", target=str(tmp_path / "mcp.json"), actual_state="present",
        state="update", conflict=None, entries=entries,
        declared_runtime_versions=(SimpleNamespace(resource_id="vision", package="@vendor/runtime", version="1.2.3"),),
    )
    malformed = SimpleNamespace(
        adapter="kiro", target=str(tmp_path / "bad.json"), actual_state="malformed",
        state="conflict", conflict="actual-malformed", entries=(), declared_runtime_versions=(),
    )
    unsafe = SimpleNamespace(
        adapter="opencode", target=str(tmp_path / "link.json"), actual_state="unsafe",
        state="conflict", conflict="actual-unsafe", entries=(), declared_runtime_versions=(),
    )
    permission = SimpleNamespace(
        adapter="zcode", target=str(tmp_path / "mode.json"), actual_state="present",
        state="permission", conflict=None, entries=(), declared_runtime_versions=(),
    )
    plan = SimpleNamespace(items=(normal, malformed, unsafe, permission))
    snapshot = SimpleNamespace(status="ok", manifest=SimpleNamespace(items=(object(),)))
    monkeypatch.setattr(doctor, "compile_sync_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(doctor, "read_mcp_manifest", lambda *args, **kwargs: snapshot)

    class Matrix:
        adapter_tools = ("cursor", "kiro", "opencode", "zcode")

        @staticmethod
        def capability(_name: str) -> SimpleNamespace:
            return SimpleNamespace(mcp=True)

    cat = SimpleNamespace(vendor_matrix=Matrix(), selected_servers=lambda *args: {})
    report = _report()
    doctor.check_mcp_plan(cat, report, "research", None, False, home=tmp_path)

    text = _messages(report)
    for state in ("missing", "changed", "stale", "unowned", "conflict", "permission", "malformed", "link-boundary"):
        assert state in text
    assert "vision declared runtime @vendor/runtime@1.2.3" in text
    summary = next(item for item in report.items if item.group == "mcp" and item.id == "sync-plan")
    assert "managed=4" in summary.message
    assert "malformed=1" in summary.message
    local = next(item for item in report.items if "server=local" in item.message)
    assert "禁止静默覆盖" in local.hint


def _write_minimal_registry(repo: Path, declarations: list[dict]) -> None:
    import yaml

    repo.mkdir(parents=True, exist_ok=True)
    (repo / "modules.yaml").write_text(yaml.safe_dump({"modules": declarations}, sort_keys=False), encoding="utf-8")


def _config(name: str, source: str, target: str, **values: object) -> dict:
    config = {
        "source": source, "target": target, "strategy": "copy", "writable": True,
        "sensitive": False, "target_mode": "0644", "preserve": [], "exclude": [],
    }
    config.update(values)
    return {"name": name, "config": config}


def test_existing_malformed_json_yaml_toml_fail_preserve_and_omit_content(
    tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    home.mkdir()
    sources = repo / "source"
    sources.mkdir(parents=True)
    declarations = []
    invalid = {
        "json": b'{"token":"DO-NOT-PRINT-JSON",',
        "yaml": b'token: "DO-NOT-PRINT-YAML"\n  broken\n',
        "toml": b'token = "DO-NOT-PRINT-TOML"\n[broken\n',
    }
    for suffix, payload in invalid.items():
        source = sources / f"config.{suffix}"
        source.write_text("{}\n" if suffix == "json" else ("key: safe\n" if suffix == "yaml" else 'key = "safe"\n'), encoding="utf-8")
        target = home / ".config" / f"bad.{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        declarations.append(_config(suffix, f"source/config.{suffix}", f"~/.config/bad.{suffix}"))
    _write_minimal_registry(repo, declarations)
    before = {suffix: (home / ".config" / f"bad.{suffix}").read_bytes() for suffix in invalid}
    report = _report()

    doctor.check_declared_formats(repo, report, home=home)

    after = {suffix: (home / ".config" / f"bad.{suffix}").read_bytes() for suffix in invalid}
    assert after == before
    failures = [item for item in report.items if item.status == doctor.STATUS_FAIL]
    assert {suffix for suffix in invalid if any(f"malformed {suffix.upper()}" in item.message for item in failures)} == set(invalid)
    output = _messages(report)
    assert "DO-NOT-PRINT" not in output
    assert "content omitted" in output


def test_real_mcp_adapter_malformed_json_is_fail_and_preserved(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_home / ".state"))
    target = tmp_home / ".cursor" / "mcp.json"
    target.parent.mkdir(parents=True)
    payload = b'{"mcpServers":{},"mcpServers":{"token":"DO-NOT-PRINT"}}'
    target.write_bytes(payload)
    cat = Catalog(ROOT)
    report = _report()

    doctor.check_mcp_plan(cat, report, "research", "cursor", False, home=tmp_home)

    assert target.read_bytes() == payload
    malformed = [item for item in report.items if "malformed" in item.id]
    assert malformed and all(item.status == doctor.STATUS_FAIL for item in malformed)
    assert "DO-NOT-PRINT" not in _messages(report)


def test_registry_boundary_root_internal_links_sensitive_modes_and_allowed_link(
    tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    source_dir = repo / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "config.txt").write_text("safe\n", encoding="utf-8")
    home.mkdir()
    declarations = [
        _config("danger", "source", "~/danger", sensitive=True, target_mode="0700"),
    ]
    _write_minimal_registry(repo, declarations)
    (home / "danger").symlink_to(source_dir, target_is_directory=True)
    report = _report()

    doctor.check_config_boundaries(repo, report, home=home)

    assert any("repository-pointing writable/sensitive root symlink" in item.message for item in report.items)
    assert any("dotf danger -c --dry-run" in item.hint for item in report.items)

    (home / "danger").unlink()
    target = home / "danger"
    target.mkdir(mode=0o755)
    secret = target / "secret.txt"
    secret.write_text("DO-NOT-READ", encoding="utf-8")
    secret.chmod(0o644)
    outside = tmp_path / "outside"
    outside.write_text("outside\n", encoding="utf-8")
    (target / "linked.txt").symlink_to(outside)
    report = _report()
    doctor.check_config_boundaries(repo, report, home=home)
    text = _messages(report)
    assert "unexpected internal symlink" in text
    assert "broad sensitive mode" in text
    assert "DO-NOT-READ" not in text

    readonly_repo = tmp_path / "readonly-repo"
    readonly_home = tmp_path / "readonly-home"
    readonly_home.mkdir()
    source = readonly_repo / "single.conf"
    source.parent.mkdir(parents=True)
    source.write_text("safe\n", encoding="utf-8")
    _write_minimal_registry(readonly_repo, [
        _config("readonly", "single.conf", "~/single.conf", strategy="symlink", writable=False),
    ])
    (readonly_home / "single.conf").symlink_to(source)
    allowed = _report()
    doctor.check_config_boundaries(readonly_repo, allowed, home=readonly_home)
    check = next(item for item in allowed.items if item.id == "config-readonly-readonly-link")
    assert check.status == doctor.STATUS_PASS


def _backup_metadata(path: Path, created_at: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": 1, "sensitive": True,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }), encoding="utf-8")


def test_sensitive_backup_retention_exact_boundary_override_and_no_content_read(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_home / ".state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    now = datetime(2026, 9, 4, tzinfo=timezone.utc)
    metadata = state / "dotf" / "backups" / "run" / ".dotf-backup.json"
    secret = metadata.parent / "secret.bin"
    _backup_metadata(metadata, now - timedelta(days=3))
    secret.write_text("DO-NOT-READ", encoding="utf-8")
    secret.chmod(0)
    policy = {"sensitive_backups": {"retention_days": 3, "metadata_filename": ".dotf-backup.json"}}

    boundary = _report()
    doctor.check_sensitive_backups(policy, boundary, home=tmp_home, now=now)
    assert not any("backup-expired" in item.id for item in boundary.items)

    _backup_metadata(metadata, now - timedelta(days=3, seconds=1))
    expired = _report()
    doctor.check_sensitive_backups(policy, expired, home=tmp_home, now=now)
    assert any("backup-expired" in item.id and item.status == doctor.STATUS_WARN for item in expired.items)
    output = _messages(expired)
    assert "DO-NOT-READ" not in output
    assert "retention=3d" in output


def test_private_runtime_artifact_reports_path_without_reading(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    artifact = root / ".agents" / "state" / "session.bin"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("DO-NOT-READ", encoding="utf-8")
    artifact.chmod(0)
    report = _report()

    doctor.check_private_runtime_artifacts(
        root, {"private_runtime": {"forbidden_in_repo": [".agents/state/**"]}}, report,
    )

    output = _messages(report)
    assert "private runtime artifact" in output
    assert "DO-NOT-READ" not in output
    assert "content_reads=0" in output


def test_tracked_source_scan_counts_skips_rule_version_and_never_value(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    agents = root / "agents"
    agents.mkdir(parents=True)
    secret = "TRACKED-SECRET-VALUE-123456"
    (agents / "source.py").write_text(f'api_key = "{secret}"\n', encoding="utf-8")
    (agents / "binary.bin").write_bytes(b"\x00binary")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "agents/source.py", "agents/binary.bin"], check=True)
    security = {
        "sensitive_patterns": [{
            "name": "api-key", "pattern": r"api_key\s*=\s*\"[A-Z0-9-]{16,}\"", "severity": "fail",
        }],
        "scan": {
            "rule_version": 7, "tracked_roots": ["agents"],
            "text_extensions": [".py"], "exclude": [],
        },
    }
    report = _report()

    doctor.check_security_scan(root, security, report)

    output = _messages(report)
    assert "rule_version=7 scanned=1 skipped=1 findings=1" in output
    assert "agents/source.py" in output
    assert secret not in output
    assert "value omitted" in output


def test_canonical_text_json_parity_redaction_and_exit_threshold(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "PARITY-SECRET-VALUE-123456"
    monkeypatch.setenv("DOCTOR_API_TOKEN", secret)
    report = _report()
    report.add("security", "redaction", doctor.STATUS_WARN, f"Authorization: Bearer {secret}", f"token={secret}")

    payload = json.loads(doctor.format_json(report))
    text = doctor.format_text(report, verbose=True)

    assert payload["checks"] == [asdict(item) for item in report.items]
    assert secret not in json.dumps(payload) + text
    canonical = payload["checks"][0]
    assert canonical["status"] == doctor.STATUS_WARN
    assert canonical["id"] in text and canonical["message"] in text and canonical["hint"] in text
    assert doctor.exit_code(report, "fail") == 0
    assert doctor.exit_code(report, "warn") == 1
    report.add("mcp", "broken", doctor.STATUS_FAIL, "failed")
    assert doctor.exit_code(report, "fail") == 1


def test_planner_failure_does_not_stop_unrelated_checks(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_home / ".state"))

    def fail_mcp(*args: object, **kwargs: object) -> None:
        raise RuntimeError("planner unavailable")

    def skills_ok(_root: Path, report: doctor.DoctorReport, **kwargs: object) -> None:
        report.add("skills", "continued", doctor.STATUS_PASS, "unrelated check continued")

    monkeypatch.setattr(doctor, "check_mcp_plan", fail_mcp)
    monkeypatch.setattr(doctor, "check_skills_plan", skills_ok)
    args = argparse.Namespace(
        profile="research", tool="cursor", deep=False, json=True,
        verbose=False, fail_on="fail", root=ROOT,
    )

    report = doctor.build_report(args)

    assert any(item.group == "mcp" and item.status == doctor.STATUS_FAIL for item in report.items)
    assert any(item.group == "skills" and item.id == "continued" and item.status == doctor.STATUS_PASS for item in report.items)


def test_legacy_doctor_module_is_import_only_and_gitignore_untouched() -> None:
    source = (ROOT / "scripts" / "agents" / "doctor_impl.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    assert "from doctor import" in source
    assert (ROOT / ".gitignore").is_file()
