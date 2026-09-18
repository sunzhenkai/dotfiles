# Agent Roster Flow

一次跨 agent 的任务编排：按 Track 走完一组 Stage，每个 Stage 确认 Assignment。需要人点头的选择只在 Orchestrator 会话里收集；执行性工作才发出 Delegation。

本文件只收 Flow 自己的词。Endpoint / Agent Kind / Orchestrator / Delegation / Handoff / Run / Trace 沿用 agent-roster 仓的 `CONTEXT.md`，这里不重定义。

## Language

**Flow**:
一次从理解到收尾的多 Stage 编排。
_Avoid_: acpx flow, pipeline, 工作流（含糊时）

**Stage**:
Flow 上的一段。固定顺序：理解、定方案、方案评审、实现、代码评审、收尾。
_Avoid_: 步骤, phase, step

**Track**:
Simple / Medium / Complex。只改每个 Stage 绑定的 skill 与产物，不改 Stage 顺序。
_Avoid_: 模式, 级别, 难度

**Assignment**:
某个 Stage 上确认的 Endpoint + Model，或 `human`。
_Avoid_: agent, 执行者

**human**:
一种 Assignment：该 Stage 由使用者拍板，不发出 Delegation。
_Avoid_: 本会话, 自任, skip

**Decision Surface**:
Orchestrator 与使用者的当前会话。所有需要人点头的选择只在这里收集。
_Avoid_: 主 agent（与 Orchestrator 同指时）, 把确认丢进受派会话

**Frozen Input**:
派出前已在 Decision Surface 敲死、写入委派 prompt 的决定。受派方不得再问同一件事。
_Avoid_: 让受派方澄清后再做

**Resident Stage**:
对话与决策在 Decision Surface 完成、不发出 Delegation 的 Stage。仍须在 spine 记录当时 Orchestrator 的 Agent Kind 与 Model。
_Avoid_: 自任执行, human（那是使用者拍板，不是编排者在本会话做决策性工作）

**Optional Stage**:
可以整段不发生的 Stage。v1 里只有代码评审。跳过 ≠ `human`。
_Avoid_: 把可选并进相邻 Stage

**Plan Review**:
实现之前对方案产物的审查。
_Avoid_: 评审（单独出现时）

**Code Review**:
实现之后可选的 Git diff 级审查，绑定 `$dotf-code-review`。
_Avoid_: 评审（单独出现时）, 用通用 agent 逐文件看代码
