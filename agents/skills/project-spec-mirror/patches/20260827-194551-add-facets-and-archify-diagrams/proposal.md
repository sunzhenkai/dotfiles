# 增加工程切面并委托 archify 出图

- target: agents/skills/project-spec-mirror
- mode: update
- patch: 20260827-194551-add-facets-and-archify-diagrams
- risk: medium
- status: proposed

## Intent

在金字塔之外维护工程切面（SOURCE / CONTRACT / SLICE / VERIFY / TRAFFIC）与垂直切片生命周期；图表委托已安装的 `archify`（https://github.com/tt-a1i/archify），产物写入 `diagrams/`。切片不必等全部契约写完。

非目标：不实现业务代码；不把 PHP/Go 写死为唯一语言对；不把 archify 源码/schema 拷进本 Skill；不再做一次 self-upgrade。

## Conflict check

与「不要额外再造顶层分类」冲突，改为允许 `facets/` 与 `diagrams/`。不替代 concepts/entities/flows/modules。与 pretty-view-html/html-diagram：本 Skill 的工程图走 archify，不改那个 Skill。

## Rationale

可执行契约 + 垂直切片是跨项目仍成立的读/改规格方式。archify 用公开仓库引用，环境未安装时表格兜底。init 骨架与 validate、unittest 可验证。

## Files

- `SKILL.md` — build/update/maintain 切面与 archify
- `references/layout.md` — 目录与阅读顺序
- `references/knowledge.md` — 切片交叉链接
- `references/facets.md` — 切面规则（新）
- `references/diagrams.md` — archify 引用（新）
- `scripts/specctl.py` — 骨架与 validate
- `tests/test_specctl.py` / `tests/test_skill_contract.py`
- `evals/cases.yaml`

## Validation

- 应用前：`git apply --check --recount`
- 应用后：unittest discover；frontmatter；无私有信息
