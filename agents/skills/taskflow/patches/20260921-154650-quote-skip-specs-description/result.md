# Result

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-154650-quote-skip-specs-description
- risk: low
- status: applied
- applied-at: 2026-09-21T15:47+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `yaml.safe_load(evals/cases.yaml)` pass（15 cases）
- privacy check: pass
- mode check: pass

## Notes

单行引用风格修复，无语义变化。该缺陷在 HEAD 已存在（`description: driver 必须显式 skip_specs: true` 含裸 `: `），由上一个 patch 的应用后验证发现。
