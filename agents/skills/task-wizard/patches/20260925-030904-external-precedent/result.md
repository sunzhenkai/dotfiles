# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-030904-external-precedent
- risk: high
- status: applied
- applied-at: 2026-09-25T03:09:25+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

frontmatter `name` 仍为 `task-wizard`。简单/中等路由未改为检索仓外。复杂档指向 `references/external-precedent.md`。Goal 仍经审阅，且审阅在外部参照之后。task-explore 不在本轮。
