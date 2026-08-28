# Result

- target: agents/skills/project-spec-mirror
- patch: 20260828-211654-important-method-full-logic
- risk: medium
- status: failed
- applied-at: 2026-08-28T21:16:54+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — fail（`test_important_briefs_not_omits` 找不到 `不得整份省略`）
- privacy check: pass

## Notes

生产文件已应用。方法层规则已写入，但 modes.md 丢掉了上一轮文件层禁令措辞 `不得整份省略`，导致既有 contract 测试失败。本目录不再改写；修复见后续 patch。
