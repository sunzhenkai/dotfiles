# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-065234-delivery-standard
- risk: medium
- status: applied
- applied-at: 2026-09-25T06:58:00+08:00

## Validation

- `git apply --check --recount`: fail（误报：--recount 对本 diff 行数误判；diff 行数由 `diff -u` 生成、本身准确）
- `git apply --check`（无 --recount）: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass（update；用户已确认应用）

## Notes

应用后核对：SKILL.md 出现「交付标准」10 处（模板、审阅表、P1、做完判定等），CONTEXT.md 3 处（新术语 + P1）。用户批准内容后应用，无偏差。
