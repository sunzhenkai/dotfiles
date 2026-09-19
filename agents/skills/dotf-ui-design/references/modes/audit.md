# Audit 模式

既有界面在其自身设计系统内的问题排查、一致性审查、设计 handoff。产出 findings 报告 + design-plans/ 计划；只读产品源码。

按 [../improve-ui/SKILL.md](../improve-ui/SKILL.md) 执行，骨架：

1. **选面**：尊重用户范围；一个应用、一个 surface family；从路由与布局出发追渲染路径，不做全仓库不一致搜索。
2. **重建局部系统**：DESIGN.md / 仓库指引 / surface 文档，只认当前有效的；记录 Design language 块。
3. **证明**：finding 三证齐全（契约、运行时、修正），缺一即弃；宁要没有 finding，不要立不住的 finding。
4. **证伪**：逐条回读引用源尝试推翻；推翻即删。
5. **报告**：Design language + findings 表（最多 3 条，按置信度/影响排序）+ Improve first（只选一条）；停下问用户选哪些写计划。
6. **计划**：一条变更一份计划，用 [../improve-ui/references/plan-template.md](../improve-ui/references/plan-template.md)；落盘、状态与承接见 [../plans.md](../plans.md)。

## Override（与 vendor 冲突时以本节为准）

| 项 | vendor | 本 skill |
| --- | --- | --- |
| 计划目录 | `design-plans/` | 一致；该目录另有用途时改 `ui-design-plans/`，见 plans.md |
| 计划索引 | 未规定 | `design-plans/README.md` 台账，字段见 plans.md |
| 严重度 | 只有 Confidence | 台账统一用 priority（P0/P1/P2），推导规则见 plans.md |
| 深度档位 | 未规定 | `quick`（只查高频组件，仍最多 3 条）/ `standard`（默认，全部交互 UI）/ `deep`（含营销页） |
| 取证方式 | 用户自带或明确要求视觉检查时才用 rendered evidence | 触发面不变；需要采集时按 [../visual-evidence.md](../visual-evidence.md)，证据带采集条件 |

## 设计系统缺位

反复因缺少契约证据（无 DESIGN.md / token 体系 / 文档化决策）证不成 finding 时，停止审计而不是放宽证明标准：把证不成的候选记录为"待契约"清单交给用户，并将设计系统沉淀明确转交 ui-template-design（创建 / 领养 / 迭代项目的 design-system Active Instance）；契约就位后再恢复审计。

## 品味判断

audit 不引入新品味，只对照 surface 自己的设计证据；品味源头与 design 模式同出 [../frontend-design/SKILL.md](../frontend-design/SKILL.md)。
