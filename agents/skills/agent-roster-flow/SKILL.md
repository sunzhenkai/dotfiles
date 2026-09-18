---
id: agent-roster-flow
name: agent-roster-flow
description: 按 Stage 编排跨 agent 任务：理解、定方案、方案评审、实现、可选代码评审、收尾。每段在本会话确认 Assignment（Endpoint+Model 或 human），执行才委托 $agent-roster。用于多 agent 工作流、跨 agent 分步选人、每步选 Endpoint 和模型。普通单次修复不要加载。
---

# Agent Roster Flow

面向用户默认简体中文。命令名、路径、代码、状态值与既成术语保持原文。术语见 [CONTEXT.md](CONTEXT.md)。

依赖 `$agent-roster`。本 skill 不直接调用 `acpx`。

## 加载

先读本文件。确认 Track 之后读 [references/tracks.md](references/tracks.md)。进入某个 Stage 再读 [references/stages.md](references/stages.md) 对应节，不要预加载其它 Stage。新建或恢复 Flow 时读 [references/spine.md](references/spine.md)。

## 一次 Flow

```text
- [ ] 1 绑定 Flow Instance（新建或恢复 spine）
- [ ] 2 理解（Resident）：对话 skill + 建议 Track，等人确认
- [ ] 3 按 Stage 顺序推进：本会话确认 Assignment → 需要派出才委托 $agent-roster
- [ ] 4 实现结束后问是否做代码评审（Simple 默认跳过；Medium / Complex 默认建议）
- [ ] 5 收尾
```

Stage 串行。Complex 实现里子 change 的并行由 `$taskflow` 负责。

## 不变量

1. **Decision Surface**：需要人点头的选择只在 Orchestrator 当前会话收集。受派 prompt 只含 Frozen Input；受派方执行，不再提问。
2. **执行才派出**：理解不派出。实现与代码评审一旦进入就必须派出。编排者不得自任执行。
3. **先确认后派出**：每个 Stage 开始前确认 Assignment 并写入 spine。派出前还要按 `$agent-roster` 写 `decision.md`（必须早于执行）。
4. **菜单来自脚本**：Assignment 选项只来自 `scripts/list_assignments.py`。名册里没有的 Endpoint 不存在。菜单没有的 Model 允许手打 id。
5. **model 进契约**：委托 `$agent-roster` 时带上已确认的 Endpoint 与 Model。契约没有 `model` 字段就停下报告，不要把模型只写进 prompt 指望受派方遵守。

## 绑定

`flow_id` = `<YYYYMMDD-HHMMSS>-<slug>`。spine 在 `~/.cache/agent-roster/flows/<flow_id>/`。

- 使用者要继续上次：读 cache 下列出进行中的 spine，选一个再恢复。格式见 [references/spine.md](references/spine.md)。
- 否则新建 spine，记下任务一句话与工作目录。
- 未写入 spine 不得进入理解之后的 Stage。

## Assignment

每个 Stage 开始时在本会话确认。完成标准：spine 里该 Stage 有一行 Endpoint + Model（Resident 记 Orchestrator 的 Kind + Model；`human` 只出现在方案评审与收尾）。

派出前：

```bash
python3 <skill-dir>/scripts/list_assignments.py --stage <stage-id> [--probe]
```

把 JSON 收成编号表，标出推荐行（读 `$agent-roster` 的 `routing.md`、相关画像与 Trace；规则为空就跳过，证据不足就说「无推荐」）。等人回复编号、`沿用` 或 `endpoint + model`。未收到选择不得发出 Delegation。

`--stage` 取值：`understand` · `plan` · `plan-review` · `implement` · `code-review` · `wrap-up`。脚本决定该 Stage 是否提供 `human`。模型清单格式在需要写 `<data_root>/agents/models.yaml` 时再读 [references/models-yaml.md](references/models-yaml.md)。

Resident Stage（理解）不派出：仍在 spine 记录当前 Orchestrator 的 Agent Kind 与 Model，并向使用者亮出来。

## 委托

只在 Assignment 不是 `human`、且该 Stage 需要派出时。完成标准：`$agent-roster` 返回 `completed` / `failed` / `timeout`，且 Handoff 路径已写入 spine。

1. 加载 `$agent-roster`。使用者已选定唯一 Endpoint，走它的快速路径。
2. 契约字段：`endpoint`、`model`、`prompt`（Frozen Input + 上一 Stage Handoff 路径）、`cwd`、`permission`、`handoff`、`timeout`。
3. `permission`：方案评审只读；定方案（写产物）、实现、代码评审、收尾里的 archive / commit 为可写。实现可写前工作树不干净就先问。代码评审可写且允许脏工作树（对象可以是 uncommitted diff），在 `decision.md` 写明这是 Stage 级例外。
4. 下一 Stage 只读上一棒 Handoff 路径，不把完整输出塞进 prompt。

失败分类与返工按 `$agent-roster`。换人、改 prompt、是否重试：回到本会话再确认，不在受派方里问。

## Track

理解结束时建议 Simple / Medium / Complex，等人确认后写入 spine。之后才读 [references/tracks.md](references/tracks.md) 按该 Track 绑定 skill。

允许升级。已经有 OpenSpec change 或 `{task}-driver` 时不得悄悄降级；要降级必须使用者明确同意并处理已有产物。

## 可选代码评审

实现 Stage 完成后停在本会话：做或跳过。跳过则该 Stage 不发生、不跑脚本。选做才确认 Assignment 并派出。范围门（uncommitted / 默认分支 / MR）也在本会话问完，写入 Frozen Input；受派方执行 `$dotf-code-review`，不再改范围。
