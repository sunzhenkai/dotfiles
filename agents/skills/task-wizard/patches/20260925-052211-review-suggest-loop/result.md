# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-052211-review-suggest-loop
- risk: high
- status: applied
- applied-at: 2026-09-25T05:23:16+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

审阅循环改为：出方案 → 评审（定级 + 改进意见）→ 修改方案 → 再评审。开工门是改进意见「已达到预期」。「审阅不通过」只用于诚实结论：对照已有知识、已有方案、公开方案也无法再完善以达到预期。同一缺口还在不再单独停。

契约同步（不在本 patch 路径内）：`openspec/specs/task-wizard-goal/spec.md`，`docs/adr/0028-review-loop-until-expected-or-honest-stop.md`，`0025` 与 `0027` 的取代说明。未 sync、未 commit、未 push。
