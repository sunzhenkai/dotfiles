# Result

- target: agents/skills/taskflow
- patch: 20260828-231347-dirty-task-skip-ask
- risk: medium
- status: applied
- applied-at: 2026-08-28T23:14:25+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `evals/cases.yaml` 的 `fail-closed-must-repos` 已与新门禁对齐；无独立 runner
- privacy check: pass

## Notes

实际 diff 与 proposal / `change.patch` 一致。`name` 仍为 `taskflow`。未改镜像目录，未 commit / sync / push。已有 driver 里逐字抄过的旧协议文本不在本 patch 范围。
