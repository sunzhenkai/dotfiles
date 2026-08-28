# 增加 specctl route 与 set-sync --hotspot

- target: agents/skills/project-spec-mirror
- mode: update
- patch: 20260828-145505-specctl-route
- risk: medium
- status: proposed

## Intent

补齐文件→页的机械路由：`specctl route` 解析模块 README 的「根」/「文件」表，把 `diff` 映射到模块页；rename 走 `from`。`set-sync --hotspot` 整表回写 `.mirror.json` 的 `hotspots`。update 必须用 `route`，不再手算。

非目标：不改放置/确认门/金字塔正文规则；route 不写 Markdown；不扫全库反引号路径；知识层仍由 Agent 跟链接。

## Conflict check

替换 P0 的「有 route 则用，否则手算」。与 `test_skill_contract` 命令表同步加入 `route`。不与 OpenSpec / archify 冲突。

## Rationale

P0 已规定算法；本轮把同一算法放进 CLI，update 可测：文件表命中、前缀命中、rename、unmapped、未 build。

## Files

- `scripts/specctl.py` — `route`、`collect_diff_files`、`--hotspot`、init `hotspots`、validate 类型
- `tests/test_specctl.py` / `tests/test_skill_contract.py`
- `SKILL.md` — 命令表与 update 强制 route
- `references/routing.md` / `modes.md` / `layout.md`
- `evals/cases.yaml` — update 必须走 route

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
