# Result

- target: agents/skills/dotf-ui-design
- patch: 20260828-203800-internal-refer-skills
- risk: medium
- status: applied
- applied-at: 2026-08-28T20:38:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass（`patches/` 内 change.patch 含上游原文尾空白，属快照，未改）
- target tests: `python3 -m pytest -q tests/test_agents_skill_defaults.py agents/skills/dotf-ui-design/tests/test_skill_contract.py` → 12 passed
- privacy check: pass

## Notes

- 4 条能力 skill 已 vendor 到 `references/`；`frontend-design` 仍走全局 defaults。
- 配套（不在本 patch 内）：从 `agents/skills-defaults.yaml` 删除这 4 项，并同步 `agents/README.md` 与 `tests/test_agents_skill_defaults.py`。
- 审计 BLOCK/WARN 均为已知误报，记录在 `references/UPSTREAM.md`。
