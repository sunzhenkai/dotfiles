# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-021056-goal-plan
- risk: high
- status: applied
- applied-at: 2026-09-25T02:11:32+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

用户已确认共同理解并授权把该行为写入 skill，高风险门禁视为通过。Goal 节未重复仓库专属安装命令；任务方案里原有的示例命令未改。未 sync、未 commit、未 push。
