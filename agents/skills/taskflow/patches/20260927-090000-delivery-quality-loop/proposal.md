# taskflow 沉淀交付质量闭环与验收 rubric

- target: agents/skills/taskflow
- mode: update
- patch: 20260927-090000-delivery-quality-loop
- risk: medium
- status: proposed

## Intent

上一轮复杂交付复盘里，真正让质量闭环生效的三类经验仍只写在任务目录（`tasks/ongoing/agent-delivery-quality/`），没有进共享 skill：

1. **小切片回归闭环**：先跑一个窄切片，失败按 skill gap / implementation bug / acceptance gap 分类，skill gap 出可审计 patch，修复后只重跑受影响切片。
2. **验收 rubric**：五维（功能闭环、UI/UX、工程质量、画像一致性、证据）+ UI/UX 六子项（信息架构、视觉层级、关键状态、反馈、无障碍、响应式）+ 通过线（五维均 ≥2，UI/UX ≥2.5），评分主体按岗位分配、证据先行。
3. **实现者隔离**：实现者只收样例/需求原文与运行约束，不收质量画像、rubric、期望页面清单。

taskflow 已经是复杂交付的最终编排者，且已有 `patches/`、`evals/`、`references` 式基础设施，因此把这三类经验抽象进 taskflow，而不是新建 skill。

要改变的行为（全部在 `agents/skills/taskflow/`）：

1. 新增 `references/delivery-quality-loop.md`：小切片先行、失败三分类、证据落盘位置与命名、只重跑受影响切片、全链路验收作为最后一次。
2. 新增 `references/acceptance-rubric.md`：五维评分表、UI/UX 六子项与均值口径、评分主体、证据先行、通过线与「优秀 UI/UX」门槛。
3. 新增 `references/implementer-isolation.md`：实现者 prompt 只允许含什么、必须排除什么；如何用同一个样例原文复跑。
4. `SKILL.md` 的「propose 阶段的产出约定」收尾段说明补一句：回归按 `delivery-quality-loop` 执行，验收按 `acceptance-rubric` 评分。
5. `SKILL.md` 的「并行执行」节之后新增「实现者隔离」小节，指针指向新 reference；说明派发实现时用 `implementer-isolation`。
6. `SKILL.md` 的「质量画像与降级确认」节补一句：driver 的最终验收必须按 `acceptance-rubric` 出分，缺分不得勾验收标准。

非目标：不改阶段路由、委托契约、Driver 协议固定文本、子 change 命名与 `skip_specs` 行为；不改 `evals/cases.yaml` 已有 case 的判定语义（仅新增 case）；不引入脚本；不在 skill 里写样例项目、机器路径或私有信息；不复制质量画像字段清单进 taskflow（画像契约仍由 task-wizard 持有）。

## Conflict check

- **Driver 协议固定文本**：新内容只写在模板外的说明段与纪律节，`Driver 协议` 小节一行不动；`driver-protocol-verbatim` 与 `scaffold-three-steps` case 不受影响。
- **checkbox 唯一真相**：新增 reference 不引入第二套完成度，只规定「怎么验、怎么打分、证据放哪」，进度仍只认 checkbox；`checkbox-ssot` case 的 must_not 仍成立。
- **一轮结束三条件**：rubric 里「缺分不得勾验收标准」对应已有「不把未完成项勾成完成」，不新增结束条件。
- **质量画像与降级确认**：本轮只加指向 rubric 的一句，不改 pending/confirmed 语义与用户确认权归属。
- **并行执行节**：实现者隔离与并行执行互补——并行讲「谁做哪块」，隔离讲「派发时给什么」；不改变并行表与子代理约束。
- **evals**：只追加 case，不改动已有 case 的 id、描述与判定。
- **零脚本**：新增文件是 Markdown reference，不违反「skill 目录 MUST NOT 包含 scripts/」。

## Rationale

这三类经验是上一轮真正改变结果的动作，且与具体样例无关：任何复杂交付都能先跑窄切片、按固定维度评分、隔离实现者输入。放进 taskflow 后，下一次复杂任务不必再回读某个任务目录才知道怎么做；同时保持画像契约在 task-wizard、编排在 taskflow 的既有分工，不产生第二份字段定义。可验证点：reference 是否可读、`SKILL.md` 是否有指针、rubric 是否有明确的维度/子项/通过线、隔离节是否列清允许与排除项——都可机械核对。

## Files

- `agents/skills/taskflow/references/delivery-quality-loop.md`（新增）— 小切片回归闭环
- `agents/skills/taskflow/references/acceptance-rubric.md`（新增）— 五维与 UI/UX 六子项 rubric
- `agents/skills/taskflow/references/implementer-isolation.md`（新增）— 实现者输入隔离
- `agents/skills/taskflow/SKILL.md`（改）— propose 收尾段加回归/rubric 指针；「质量画像与降级确认」加最终验收出分要求；「并行执行」后新增「实现者隔离」小节
- `agents/skills/taskflow/evals/cases.yaml`（追加）— 4 个新 case：小切片三分类、rubric 通过线、实现者隔离、rubric 不作第二份账本
- `openspec/specs/taskflow-orchestration/spec.md`（改）— 新增 `Requirement: 交付质量闭环与验收 rubric` 与对应 Scenario，保持 skill 与 spec 一致

## Validation

- 应用后二次同步：`openspec/specs/taskflow-orchestration/spec.md` 补 `Requirement: 交付质量闭环与验收 rubric`，`openspec validate --strict --type spec taskflow-orchestration` 通过。

- 应用前：`git apply --check --recount agents/skills/taskflow/patches/20260927-090000-delivery-quality-loop/change.patch`（仓库根执行）。
- 应用后：`git diff --check -- agents/skills/taskflow`；核对实际 diff 与本 proposal 一致；`SKILL.md` frontmatter 合法且 `name` 与目录名一致；三个新 reference 的可达链接存在；`evals/cases.yaml` 仍可被解析且已有 case 未被改写；grep 确认无样例项目名、个人主机路径、凭据。
- 行为核对（人工读文本）：Driver 协议固定文本未动；进度仍只认 checkbox；未新增结束条件；实现者隔离节列清允许/排除项；rubric 含五维、UI/UX 六子项、通过线与评分主体。
- 本 patch 不自动应用、不 sync、不 commit；medium 风险按 skill-upgrader 门禁应用后补 `result.md`。
