# Agent 交付质量闭环设计

- 主设计：[delivery-quality-loop.md](delivery-quality-loop.md)
- 决策记录：[adr-quality-profile.md](adr-quality-profile.md)
- 任务：`../TASK.md`

## 一句话

为复杂 Goal 交付增加可复用的「质量画像 → 角色化审阅 → 显式降级确认 → taskflow 验收 → 小切片回归」闭环，避免把功能清单误当完成。

## 状态

design，待 decide。

## 真相源

本目录保留案例设计、取舍与审计过程。通用执行规则已上移到 `agents/skills/taskflow/references/`：

- `delivery-quality-loop.md`
- `acceptance-rubric.md`
- `implementer-isolation.md`

两者冲突时以共享 skill 为准。
