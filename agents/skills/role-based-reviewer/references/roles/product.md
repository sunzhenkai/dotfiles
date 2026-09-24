# 产品（`product`）

角色文件：仅在本角色生效时加载（见 [preload-protocol](../preload-protocol.md)）；职责边界以 [role-vocabulary](../role-vocabulary.md) 为准。级别：🔴 Blocker / 🟡 Major（门 3 默认报）/ ⚪ 默认不报，拿不准降一级。`[运行态]` 条目纯 diff 评审降级为「⚠ 需运行态验证」。

## 优先锚点

需求、spec、概念/愿景、交互闭环。

跳过：代码实现、对接落地。

## 核心检查清单

1. 🟡 [代码] 需求闭环：主流程 + 异常/边界场景有明确行为定义，无「到时候再看」
2. 🟡 [代码] 与既有行为一致：不破坏既有用户习惯，术语与全局一致
3. 🟡 [代码] 文案：用户可见文案明确、语气一致，无内部黑话外泄
4. 🟡 [代码] 可验收：每条需求有可验证的验收标准
5. ⚪ [代码] 价值与优先级论证、明确「不做什么」
6. ⚪ [运行态] 交互闭环实际走查（与 design 清单第 1 节互补，这里看业务结果是否达成）

## 下游建议

`task-explore` / `taskflow` → 方案探索与任务编排；OpenSpec（若项目有）→ 需求结构化。

## 跨角色 redirect

- biz ↔ product（需求/spec）：消费 spec 做对接 → biz；产出 spec 做提案 → product
- design ↔ product（体验）：视觉/交互/无障碍 → design；价值/范围/文案 → product
