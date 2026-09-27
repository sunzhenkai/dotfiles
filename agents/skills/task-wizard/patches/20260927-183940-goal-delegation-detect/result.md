# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260927-183940-goal-delegation-detect
- risk: high
- status: applied
- applied-at: 2026-09-27T10:43:02Z

## Validation

- `git apply --check --recount`: pass（初版裸 `@@` 头不被接受，改为 diff -u 生成后 pass）
- `git apply --check`: pass
- `git diff --check`: pass
- target tests: not-available（纯指令文本，人工核对与 delivery-loop goal 模式无矛盾）
- privacy check: pass
- mode check: pass

## Notes

用户已确认 diff 后应用。
