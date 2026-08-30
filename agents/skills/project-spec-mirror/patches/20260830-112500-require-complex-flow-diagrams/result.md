# Result

- target: agents/skills/project-spec-mirror
- patch: 20260830-112500-require-complex-flow-diagrams
- risk: medium
- status: applied
- applied-at: 2026-08-30T11:25:26+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 49 tests OK
- privacy check: pass

## Notes

相对上一轮 adaptive-workload 策略，只把「复杂业务逻辑」收回为必配图；线性三步与装饰性结构图仍可省略。`specctl validate` 仍不机械检查 HTML 是否存在。
