# Result

- target: agents/skills/project-spec-mirror
- patch: 20260828-211828-restore-file-omit-phrase
- risk: low
- status: applied
- applied-at: 2026-08-28T21:18:28+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 32 tests, OK
- privacy check: pass

## Notes

仅在 `important` 档位补回「不得整份省略」。方法层规则来自上一 patch 的已应用正文，未改写该历史目录。未 commit / 未 sync。
