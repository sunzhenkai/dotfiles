---
id: task-grill
name: task-grill
description: taskflow 链路上 explore 之后、propose 之前的可选收敛环节。对 `{task}-driver` 做结构化访谈：决策树 + frontier 分轮提问，每题附推荐答案，问到无静默假设为止；术语与决策随访谈沉淀进 driver change 的 grill.md，不写实现代码。在 explore 后仍有多个未决分支、用户点名 grill/拷问方案、或想快速达成方案共识时使用。问题本身还没想清时不要用（先用 openspec-explore 发散）。
---

# 任务拷问（Grill）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

`taskflow` 链路上的**可选**收敛环节，位于 explore（发散）与 propose（提案）之间：

```
taskflow-new → openspec-explore? → task-grill? → openspec-propose → openspec-apply-change → openspec-archive-change
```

进度真相仍只有 OpenSpec checkbox 一种；本 skill 不建台账、不改 `proposal.md` 协议、不引入新的进度记录。

## 何时使用

- explore 之后方案已有雏形，但仍有多个未决决策分支
- 用户点名 grill、拷问、stress-test 方案
- 需要在 propose 拆分子 change 之前把决策收敛成共识，避免提案返工

## 何时不用

| 情况 | 改用 |
|------|------|
| 尚无 driver | `taskflow-new` |
| 问题本身还没想清，需要发散 | stock skill `openspec-explore`（绑定 `{task}-driver`） |
| 决策已收敛，直接拆子 change | stock skill `openspec-propose`（绑定 `{task}-driver`） |

## MUST 先做

1. 确定目标 driver：会话已明确 `{task}` 时直接用 `{task}-driver`；否则 `openspec list --json` 找唯一匹配，不唯一时列出候选请用户选，不猜。
2. 遵守 taskflow 的绑定纪律：在 driver 的 **planning root** 下工作；读 driver `proposal.md`（含协议）、`tasks.md`（如已存在）与已有 explore 结论，作为决策树的根。

## 核心机制：决策树 + frontier 分轮

把方案建模成一棵**决策树**：每个决策分支挂着依赖它的子决策。每轮计算 **frontier**——所有前置决策已落定、现在就能问的问题——一次性编号抛出，每题给出**推荐答案**，然后等待用户回答。用户的回答让已落定分支外推边界，解锁下一轮。

每轮格式：

```
❓ **Q1** - **<问题标题>**: <题干，可多段，含多个选项>

➡️ <推荐答案>

---

❓ **Q2** - **<问题标题>**: <题干>

➡️ <推荐答案>
```

规则：

- **事实是 Agent 的事，决策是用户的事**。frontier 题目需要环境事实（代码、配置、文档）时，派 sub-agent 或自行读取，不问用户；该分支的下游问题等事实回报后再问，其余 frontier 题照常抛出。
- 答案依赖本轮其他未答题目的，归入后续轮，不进本轮。
- 一轮结束后重算 frontier 再问下一轮；不预答没听到的答案。

## 伴随纪律：术语与决策沉淀

访谈同时做领域建模，随 crystallize 随记录，不攒批：

- **挑战术语冲突**：用户的用词与既有文档/代码冲突时当场指出（"文档里『取消』指整单，你刚说的像是部分取消——是哪个？"）
- **磨尖模糊词**：出现含糊或一词多义时提议精确术语（"你说的 account 是 Customer 还是 User？这俩是两回事"）
- **具体场景压测**：讨论概念边界时构造边缘场景逼迫说清边界，而非停留在抽象描述
- **与代码交叉验证**：用户陈述现状时对照实际代码，矛盾即抛出
- **ADR 门槛**：只有同时满足**难逆转 + 后人费解 + 真实取舍**三条才记为 ADR 候选，缺一不记

## 沉淀位置

只写 driver change 目录下的 `<changeRoot>/grill.md` 单文件（首次有内容时才创建）：

```markdown
# Grill：<task>

## 决策记录

| # | 决策 | 结论 | 理由 | 状态 |
|---|------|------|------|------|
| D1 | <...> | <...> | <...> | settled / open |

## 术语表

| 术语 | 本任务语境下的定义 | 与既有用词的关系 |
|------|--------------------|------------------|
| <...> | <...> | <沿用 / 修正了 X / 新造> |

## ADR 候选

<!-- 仅记录满足三门槛的；由 design.md 吸收或随 change 归档晋升 -->

- [ ] adr-<slug>: <一句话>（出处：D<N>）

## 未决问题

<frontier 尚未清空时列出；清空则写"无">
```

**禁止**在本环节写实现代码、改 `proposal.md` 的协议小节、写 `specs/` 增量、或把结论写到 driver change 以外。决策对提案的影响发生在 propose 阶段——propose 读 `grill.md`，把 settled 决策写进各子 change 的 proposal/design，ADR 候选按目标仓约定落盘。

## 结束条件

frontier 为空——决策树上每个分支都被显式回答，不存在静默假设——且**用户确认达成共识**后才算结束。未确认前不推进 propose，不基于半棵树拆子 change。

结束时按「交接」模板输出：

```
## 交接

**已收敛**：[一句话]
**决策数**：N 项 settled，M 项 ADR 候选
**沉淀位置**：`<planning_root>/openspec/changes/{task}-driver/grill.md`
**下一步**：{{slash:openspec-propose}}（绑定 `{task}-driver`，拆分子 change）
**未决问题**：[列表，或无]
```

## 边界

- 不写实现代码
- 不建台账、不写 `tasks.md`（留给 propose）、不改 driver 协议
- 拷问 relentlessly，但每题必须带推荐答案——用户多数时候只需确认或否决，保持收敛速度
- 事实题自查，决策题必问；不要替用户做决策，也不要把能查到的事实抛给用户
- `grill.md` 是 driver 的中间产物：propose 阶段吸收其结论，不单独进正式文档体系

## 相关

- `taskflow` — driver 生命周期与委托契约
- `openspec-explore` — 前置发散；问题成形靠它
- `openspec-propose` — 下游；把 grill.md 的结论收成子 change 提案
