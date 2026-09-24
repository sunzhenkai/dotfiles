# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-063810-goal-skip-route-confirm
- risk: high
- status: applied
- applied-at: 2026-09-25T06:40:42+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

用户点名的行为即本轮契约：goal 里评审收敛后不再索取路由确认。高风险门禁视为通过。`openspec/specs/task-wizard-goal/spec.md` 与 `docs/adr/0031-goal-skips-route-confirm.md` 按同一方案另行写入，不在本 patch 内。未 sync、未 commit、未 push。
