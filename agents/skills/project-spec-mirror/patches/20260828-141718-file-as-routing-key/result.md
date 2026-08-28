# Result

- target: agents/skills/project-spec-mirror
- mode: update
- patch: 20260828-141718-file-as-routing-key
- risk: high
- status: applied
- applied-at: 2026-08-28T14:21:38+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — contract tests pass；`test_specctl.DetectTest.test_non_project_requires_project_or_source` fail（本机 `/tmp/package.json` 使 `/tmp` 被当成 project root；未改 `specctl.py`，属环境既有问题）
- privacy check: pass
- mode check: pass（update，未再注入 Self-evolution）

## Notes

用户已确认完整方案（删掉每文件一页，文件只做路由键，不保留 `--per-file-pages`）。本轮仅落地 P0 文档契约：`modes`/`layout`/`routing`/`knowledge`/`facets`/`SKILL` 工作流与 evals。`specctl route` 与 `set-sync --hotspot` 留待下一轮。
