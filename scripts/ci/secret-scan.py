#!/usr/bin/env python3
"""CI gate for the canonical Git-tracked Agent/source secret scan."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

import yaml  # noqa: E402
import doctor  # noqa: E402


def main() -> int:
    security_path = ROOT / "agents" / "env" / "security.yaml"
    security = yaml.safe_load(security_path.read_text(encoding="utf-8"))
    if not isinstance(security, dict):
        print("error: security policy must be a mapping", file=sys.stderr)
        return 1

    report = doctor.DoctorReport("ci-source-scan", None, "low")
    doctor.check_security_scan(ROOT, security, report)
    for item in report.items:
        print(f"[{item.status}] {item.id}: {item.message}")

    evidence = [item for item in report.items if item.id == "tracked-scan"]
    if len(evidence) != 1:
        print("error: secret scan did not emit exactly one boundary evidence record", file=sys.stderr)
        return 1
    message = evidence[0].message
    required = ("rule_version=", "scanned=", "skipped=", "findings=")
    if not all(field in message for field in required):
        print("error: secret scan evidence is missing rule/count fields", file=sys.stderr)
        return 1
    return 1 if any(item.status == doctor.STATUS_FAIL for item in report.items) else 0


if __name__ == "__main__":
    raise SystemExit(main())
