# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-051644-review-refine-not-exit
- risk: high
- status: applied
- applied-at: 2026-09-25T05:17:49+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

正文已去掉「中 → 方案置信度不足」「低 → 理解不够」这两条退出。低或中，以及高但仍有缺陷，进入完善：建议写入方案再审，不改代码，不向用户要授权。同一缺陷再审仍在才是「审阅不通过」。

契约同步（不在本 patch 路径内）：`openspec/specs/task-wizard-goal/spec.md`，`docs/adr/0027-low-medium-review-continues-refinement.md`，`docs/adr/0025` 顶部注明被取代的那一条。未 sync、未 commit、未 push。
