# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-053829-review-scope-priority
- risk: medium
- status: applied
- applied-at: 2026-09-25T05:40:43+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

用户已确认具体收敛规则，medium 门禁视为通过。`openspec/specs/task-wizard-goal/spec.md` 与 `docs/adr/0029-review-scope-and-completion-level.md` 按同一方案另行写入，不在本 patch 内。未 sync、未 commit、未 push。
