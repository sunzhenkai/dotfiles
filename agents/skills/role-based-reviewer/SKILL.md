---
id: role-based-reviewer
name: role-based-reviewer
description: "可组合的角色化只读评审：engineer、algo、data、sre、ops、biz、product、design、qa。仅在用户显式点名（/role-based-reviewer）、指定 roles=、或明确要求按岗位/多角色视角时使用。普通「看看代码」「帮我 review」不要自动加载。"
---

# 角色化评审

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

角色化只读编排与评审入口。选择角色、加载该角色所需上下文、保留职责边界，并给出可执行结论。

`mode=ask`：按岗位回答问题、标明证据与下游建议。  
`mode=review`：真正做多视角审查，输出分级发现；默认目标为当前工作区变更。

本身不改代码、不落盘、不替代实现类 skill。用户要求修复时再动手。

## 三道门禁（防误触、防角色膨胀、防吹毛求疵）

未过门禁不得进入本 skill 的预加载与分角色审查。

1. **门 1 · 收窄触发**：仅下列情况使用；否则当普通问答/常规审查处理，不加载本 skill。
   - 用户点名本 skill，或发出 `{{slash:role-based-reviewer}}`
   - 用户写出 `roles=` / 岗位短名（如「用 algo 看」「engineer+sre review」）
   - 用户明确要求按岗位、多角色、跨职能视角看问题
   **不算触发**：单独的「看看这段」「帮我 review」「有没有 bug」「审查一下 diff」——没有岗位意图时不要自动进来。
2. **门 2 · 角色确认**：未指定 `roles` 时默认只开 **engineer**。其它角色必须有**强信号**才加（见下节）；一次推断将超过 2 个角色时，先列出候选问用户，禁止静默堆视角。文件名/目录沾边（有 CSS、有 Dockerfile、有 `model` 字样）不够。
3. **门 3 · 发现克制**：`mode=review` 默认只报 **Blocker** 与 **Major**。Minor / Suggestion 仅在用户要求「仔细 / 全面 / 含风格」时输出。不确定的不当 Blocker；没有问题就说没有，不为每个角色凑一条。

## 输入

- `roles=<逗号分隔角色>`：可选。合法值：`engineer`、`algo`、`data`、`sre`、`ops`、`biz`、`product`、`design`、`qa`。
- `mode=<ask|review>`：可选，默认 `ask`。已过门 1 且用户说评审 / review / 审查时视为 `review`。
- `<问题或变更范围>`：可选。`mode=review` 且未给范围时，默认当前工作区 `git diff`（仍受门 2：不要因此自动加角色）。

示例：

- `{{slash:role-based-reviewer}} roles=algo 排序分为何掉量`
- `{{slash:role-based-reviewer}} roles=engineer,sre mode=review 服务与部署变更`
- `{{slash:role-based-reviewer}} mode=review`：未指定 `roles` 时默认 engineer（受门 2）

## MUST 先读取

[constraints](references/constraints.md) + [preload-protocol](references/preload-protocol.md) + [brief-protocol](references/brief-protocol.md) + [role-vocabulary](references/role-vocabulary.md)。

## 视角推断（受门 2 约束）

用户显式指定的 `roles` 优先，不再增删。未指定时：

- **默认只 engineer**。不要默认带 qa / product / design。
- 额外角色要有问题或 diff **主体**上的强信号，不是「文件列表里出现过」：
  - 审查目标就是测试/可测性 → + **qa**
  - 目标就是 UI 视觉/交互/无障碍（不是顺便改了样式）→ + **design**
  - 目标就是需求/方案文档 → + **product**
  - 目标就是部署/CI/集群/密钥（不是应用代码里读了环境变量）→ + **sre**
  - 目标就是模型/策略/实验效果 → + **algo**
  - 目标就是管道/数仓/口径 → + **data**
  - 目标就是运营配置/灰度节奏 → + **ops**
  - 目标就是对外协议/多租户对接 → + **biz**
- 将超过 2 个角色：停下来问，不猜。
- 项目里没有对应域（无模型、无数仓、无对外对接）时，对应角色直接不加。

推断结果写在报告开头（启用了哪些、为什么）；用户纠正后以用户为准。

## 耗时优化（大目标必读）

- **先摸规模**：`git status --short`、`git diff --stat` 或目录文件清单，再决定读多少
- 大目标 **按模块分组** 理解意图，只对核心文件抽样精读；lockfile / 生成物 / vendor / 大资源不读内容
- 每个角色只盯本职高价值问题，不要逐行复述代码，不要为求全打开几十个文件
- 支持 subagent 时，可按角色并行派发，各自返回分级结论后汇总去重

## 流程

1. 过三道门禁。未过门 1 则不要按本 skill 执行。解析 `mode` 与 `roles`；未指定角色时按上节推断，受门 2 约束。
2. 对每个生效角色，按 [preload-protocol](references/preload-protocol.md) 加载上下文。跨角色复用同一文件，合计默认 ≤6 个文件；超出时说明原因。`mode=review` 另遵循耗时优化。
3. `mode=ask`：按角色输出独立结论、证据、边界与下游建议。
4. `mode=review`：按角色输出独立 findings，标注严重级别与 `path:line`；共享对象上标主责 / 协作 / 冲突。本 skill **自己完成审查**。
5. 合并时只去重「同一证据支持的同一风险」；不得把不同角色的结论混写成无归属意见。
6. 下一步默认只推荐一个主责动作；确需并行时写明独立任务与先后关系。

## 严重级别（`mode=review`）

- **Blocker**：必须修复（正确性错误、安全漏洞、数据丢失、无法发布）
- **Major**：应当修复（明显缺陷、架构问题、关键场景缺失）
- **Minor** / **Suggestion**：默认不报（门 3）；用户要求仔细审查时再给可读性、一致性、风格类问题

## 输出

骨架见 [brief-protocol](references/brief-protocol.md)。多角色 review 至少包含：

- 生效角色及选择依据
- 每个角色独立的 findings / 证据 / 下游建议
- 共享风险的主责与协作角色
- 未知项、角色间分歧（如有）
- 统一的下一步与总结置信度
