# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260924-014036-add-task-explore-route
- risk: medium
- status: applied
- applied-at: 2026-09-24T02:05:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git apply --recount`: pass
- `git diff --check -- agents/skills/task-wizard`: pass
- frontmatter：`name: task-wizard` 与目录名一致；description 路由串已含 `grill-with-docs / OpenSpec / task-explore+taskflow / 直接实现`
- privacy check: pass（无个人/私有信息）
- mode check: pass（纯 update，未新增自进化目录；未改历史 patches）

## Notes

用户在 medium 风险门禁明确批准本 diff 并指示「应用」。

路由表按用户定义重排为三档：

- 简单：产出步骤 → 走 grill-with-docs 拷问、梳理清楚 → 直接按步骤实现
- 中等：简单之外（在简单之上），走 OpenSpec 流程实现（`openspec-propose` → `openspec-apply-change`）
- 复杂：走 task-explore → taskflow（task-explore 梳理清楚后 `handoff` 给 taskflow）

要点新增：「先拷问后实现」（简单/中等前置）、grill-with-docs 两跳调用逐字保留（`grilling` + `domain-modeling`）、下游原文带入。未触及「原则 / 工作流 / 输出模板 / 边界」。

## 已知冲突（已向用户说明）

`grill-with-docs` 内部会调 `domain-modeling`，后者写仓库根 `CONTEXT.md` / `docs/adr/`；task-explore 的 `explore` 阶段明令禁止该调用（落点冲突）。故复杂档走 task-explore 自身，不与 grill-with-docs 叠加——与用户「复杂走 task-explore → taskflow」一致。

## 未做

未 sync（`dotf agents -c`）、未 commit、未 push。
