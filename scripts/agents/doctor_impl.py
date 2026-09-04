#!/usr/bin/env python3
"""Compatibility imports for the canonical :mod:`doctor` implementation.

New callers must execute ``scripts/agents/doctor.py``.  This module intentionally
contains no check, status, rendering, exit-code, or sanitizing logic.
"""

from doctor import (  # noqa: F401
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SKIP,
    STATUS_WARN,
    CheckItem,
    DoctorReport,
    build_next_steps,
    build_report,
    canonical_payload,
    check_agents,
    check_browser,
    check_config_boundaries,
    check_declared_formats,
    check_env,
    check_mcp_plan,
    check_private_runtime_artifacts,
    check_security_scan,
    check_sensitive_backups,
    check_skills_plan,
    check_tools,
    exit_code,
    format_json,
    format_text,
    main,
    parse_args,
    run_cmd,
    run_mcp_browser_probe,
    summarize,
)


if __name__ == "__main__":
    raise SystemExit(main())
