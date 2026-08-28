# Result

- target: agents/skills/project-spec-mirror
- patch: 20260828-170810-skip-third-party-and-foreign-repos
- risk: medium
- status: applied
- applied-at: 2026-08-28T17:12:39+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 本轮新增 4 个用例及 contract 全部通过；`DetectTest.test_non_project_requires_project_or_source` 失败（应用前已存在，与本 patch 无关）
- privacy check: pass

## Notes

实际 diff 与 proposal 一致：Agent 规则、inventory/diff/route/symbols 过滤、忽略目录、嵌套 git/submodule。未改放置规则，未把 `deps/` / `third_party/` 这类可能属于本工程的目录名一律忽略。未 commit / 未 sync。
