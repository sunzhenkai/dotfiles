# Result

- target: agents/skills/task-explore
- mode: update
- patch: 20260925-031138-external-precedent
- risk: high
- status: applied
- applied-at: 2026-09-25T03:11:57+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python -m unittest agents/skills/task-explore/tests/test_task_explore_contract.py` — 41 tests OK
- privacy check: pass
- mode check: pass

## Notes

frontmatter `name` 仍为 `task-explore`。grilling 禁止项仍在。未另建词汇表。未改 decide / handoff / archive。
