# Result

- target: agents/skills/service-manager
- mode: update
- patch: 20260915-212805-generic-evolution-routing
- risk: medium
- status: applied
- applied-at: 2026-09-15T21:28:20+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- mode check: pass

## Notes

Self-evolution 目录树改为 `<skill-dir>/`；生产稿与 `evals/cases.yaml` 不再点名 `pwd-skill-manager`。历史 `patches/` 未改。
