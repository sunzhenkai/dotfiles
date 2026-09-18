# Track 绑定

确认 Track 之后读本文件。只读当前 Track 那一节。

Stage 顺序不因 Track 改变。Track 只改每个 Stage 绑定的 skill 与产物路径。

Medium / Complex 的 Handoff 用各 skill 已有路径，不复制第二份。Simple 的 plan 写在 `~/.cache/agent-roster/flows/<flow_id>/handoffs/`。

## Simple

| Stage | Resident | 派出 | 绑定 |
|---|---|---|---|
| 理解 | 是 | 否 | `$grill-with-docs` 推荐；需求已清可跳过 grill |
| 定方案 | 澄清在本会话 | 可不再派 | 轻量 plan Handoff；本会话写完即可 |
| 方案评审 | 确认 Assignment；默认推荐 `human` | Assignment 不是 `human` 时只读审 plan | 不默认绑评审 skill；点名岗位时才 `$role-based-reviewer` |
| 实现 | 确认 Assignment | 必须 | 按 plan 改代码 |
| 代码评审 | 默认跳过 | 选做则必须 | `$dotf-code-review` |
| 收尾 | 确认；默认可 `human` | 需要时 | 摘要；可选 `$commit-push` |

## Medium

| Stage | Resident | 派出 | 绑定 |
|---|---|---|---|
| 理解 | 是 | 否 | `$grill-with-docs` 推荐 |
| 定方案 | 澄清、选方案 | 写产物时 | 含糊则 `$openspec-explore`，然后 `$openspec-propose`。澄清在本会话完成后再派 |
| 方案评审 | 确认 Assignment | 只读 | 审 proposal / design / specs；不过不得 apply |
| 实现 | 确认 Assignment | 必须 | `$openspec-apply-change` |
| 代码评审 | 默认建议做 | 选做则必须 | `$dotf-code-review` |
| 收尾 | 确认 Assignment | 需要时 | `$openspec-archive-change`；可选 `$commit-push` |

## Complex

| Stage | Resident | 派出 | 绑定 |
|---|---|---|---|
| 理解 | 是 | 否 | `$task-explore` `new` / `explore`（其 explore 只委托 `grilling`，不调用 `grill-with-docs`） |
| 定方案 | 澄清、decide | 写产物时 | `$task-explore design` 可选 → `decide` → `handoff` → `$taskflow` `taskflow-new` → `$openspec-propose`。`handoff` 仍属本 Stage，不写代码 |
| 方案评审 | 确认 Assignment | 只读 | 审 design + driver / 子 change 产物 |
| 实现 | 确认 Assignment | 必须 | `$taskflow` 实施子 change |
| 代码评审 | 默认建议做 | 选做则必须 | `$dotf-code-review` |
| 收尾 | 确认 Assignment | 需要时 | 归档 driver；探索任务已在 handoff 归档；可选 `$commit-push` |
