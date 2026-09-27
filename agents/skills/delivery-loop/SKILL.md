---
name: delivery-loop
description: "把一句复杂交付目标编排成自动闭环：task-wizard 质量画像、task-explore 探索、taskflow 小切片、实现与运行证据、product/design/engineer 评审、失败归因、修复和复验。仅在用户明确要求自闭环交付、自动探索加自动验证、或短目标端到端实现时使用；简单局部修改、只要方案、或未授权多阶段编排时不进入。支持 `goal:` 模式：显式指定或自动检测到进行中 goal 时，调用 task-wizard 改走其 Goal 方案路径。"
---

# Delivery Loop

把用户的短目标变成可验证交付，而不是一次性生成大而全的实现。本 skill 是**薄编排层**：不新建第二份任务账本，不复制 taskflow 的质量规则；进度以 taskflow checkbox 为唯一真相。

## 输入

```text
delivery-loop <一句话目标>
delivery-loop goal: <一句话目标>
```

可识别的前缀：

- `normal:` 默认，真实交付。
- `goal:` 显式 goal 模式，调用 task-wizard 时走其「Goal 方案」分支。
- `benchmark:` / `盲测:` / `回归复跑:` 只用于评估 skill 或 agent 能力。

未显式标记 benchmark 时一律按 normal 处理。

**goal 自动识别**：处理前缀前先判断——消息里看得到 `/goal`，或当前有进行中的 goal 且本条消息挂了本 skill。命中即按 goal 模式执行，不需要显式 `goal:` 前缀；未命中时按 normal / benchmark 处理。

## 依赖

本轮真正执行前，确认下列 skill 可读；缺任一项停下报告安装选项，不发明等价流程：

- task-wizard
- task-explore
- taskflow
- role-based-reviewer
- skill-upgrader（仅 failure 归因为 skill gap 时需要）

## 主循环

1. **接收目标**：逐字保留目标原文，记录模式、预算、工作区和验证产物位置。
2. **生成方案**：调用 task-wizard。用户点名 `delivery-loop` 已表示接受自动编排；这不授权危险操作、线上动作、提交或部署。goal 模式下明确要求 task-wizard 走其「Goal 方案」分支（正文 → 外部参照 → 审阅 → 档位路由），并把本循环内所有向用户确认的决定改为走 task-wizard 的「审阅」，不列选项；复杂门之后其余阶段不变。
3. **复杂门**：只继续项目级 / 多模块 / 多角色 / 持久化 / 产品面广的复杂目标。简单或局部任务退出本 skill，不硬套闭环。
4. **预算**：用户未给预算时，不虚构时间或 token 限额，按 Stage 9 的默认节奏执行；用户另给时间 / 轮次 / 资源预算时以用户值为上限。
5. **探索冻结**：按 task-wizard 路由进入 task-explore，完成 explore → design → decide。
6. **taskflow 交接**：交给 taskflow 建 driver 与子 change；后续进度只认 driver / 子 change checkbox。
7. **首轮窄切片**：只选 1-3 个能从入口走到结束状态的核心闭环，先实现、测试、留证据。
8. **实现派发**：normal 必须给实现者质量画像或保留语义的子范围裁剪；benchmark 只给目标原文与运行约束。
9. **三角色评审**：调用 `role-based-reviewer mode=review roles=product,design,engineer`，先证据后评分。
10. **失败归因**：每条 Blocker / Major 只归因为 skill gap、implementation bug 或 acceptance gap；不许笼统“再改改”。归因前按 [归因自检](references/loop-protocol.md#stage-8--failure-triage)确认同一 finding 没有第二种解释、且修复层次已分清。
11. **修复复验**：skill gap 走 skill-upgrader patch；implementation bug 修交付仓；acceptance gap 补验收标准。修复后按 [增量验证协议](references/loop-protocol.md#增量验证协议)只重跑受影响门禁，Stage 10 再跑全链路。
12. **完成报告**：按完成门输出证据、分数、剩余限制和后续动作。

详细阶段、停止条件和修复轮次读 [references/loop-protocol.md](references/loop-protocol.md)。  
benchmark 输入隔离读 [references/benchmark-isolation.md](references/benchmark-isolation.md)。  
证据清单与最终报告读 [references/evidence-report.md](references/evidence-report.md)。

## 硬边界

- 不自动 commit、push、部署、改线上数据。
- pending 生产性降级必须停下等用户确认。
- 同一验证连续失败两次、或同一窄切片修复两轮仍有 P0/P1，停止并输出诚实报告。
- 不把 benchmark 的隐藏期望带给实现者。
- 不把具体项目名、机器路径、凭据写进共享 skill。
