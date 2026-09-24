# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-062351-review-recheck
- risk: high
- status: applied
- applied-at: 2026-09-25T06:24:59+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available；走读通过：P1×2 与 P2×4 且第一次核对两条 P1 已消失时，审阅节写明完成程度为高并收敛；派审贴上完成判据与「不做的事」，只写「范围同前」作废；边界外新行为不编号、不写入
- privacy check: pass
- mode check: pass

## Notes

高风险门禁：用户在看过 `goal-review-recheck` 工件后说 apply，视为批准该具体改动。description 只加了再审核对与同一条再核仍在则停，没有写入两次核对的预算。预算只在审阅节。
