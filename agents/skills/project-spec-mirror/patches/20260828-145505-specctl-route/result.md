# Result

- target: agents/skills/project-spec-mirror
- mode: update
- patch: 20260828-145505-specctl-route
- risk: medium
- status: applied
- applied-at: 2026-08-28T14:58:14+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 24 pass / 1 fail。失败项仍是 `DetectTest.test_non_project_requires_project_or_source`（`/tmp/package.json` 使 `/tmp` 被当成 project root）；本轮新增的 route / hotspot / parse 用例全部通过。
- privacy check: pass
- mode check: pass（update，未再注入 Self-evolution）

## Notes

`specctl route` 解析模块 README 的「根」/`Roots`、「文件」/`Files` 表；update 强制走 `route`。`set-sync --hotspot` 整表写回 `hotspots`。init 骨架带 `hotspots: []`。方案两轮 patch 均已应用，未 commit。
