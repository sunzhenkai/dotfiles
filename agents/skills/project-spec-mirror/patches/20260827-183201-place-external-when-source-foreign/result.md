# Result

- target: agents/skills/project-spec-mirror
- patch: 20260827-183201-place-external-when-source-foreign
- risk: medium
- status: applied
- applied-at: 2026-08-27T10:33:25Z

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 19 tests OK
- privacy check: pass

## Notes

`detect` 在工作区 git 根 + 外来 `--project/--source` 时落到 `spec/<project>/`。未迁移已误放在仓根 `spec/` 的既有镜像。未执行 sync / commit / push。
