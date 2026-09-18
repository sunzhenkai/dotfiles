# Stage 详情

进入某个 Stage 后只读对应节。Frozen Input 必须在本会话敲死后再写入委派 prompt。

## 理解 `understand`

Resident。不派出。

Simple / Medium：推荐 `$grill-with-docs`。需求已清且使用者同意，可跳过 grill。Complex：`$task-explore` 的 `new` / `explore`。

完成标准：任务一句话可检验；Track 已写入 spine；Orchestrator 的 Kind + Model 已记录。

## 定方案 `plan`

澄清、选方案、写 Frozen Input 在本会话。Simple 的 plan 本会话写入 cache Handoff 即可，可不再派。Medium / Complex 写 OpenSpec / design 产物时派出，prompt 只含已选方案与约束。

完成标准：该 Track 的方案产物路径已写入 spine。Simple 至少有目标 / 改哪里 / 不做啥。

## 方案评审 `plan-review`

审方案，不审代码。默认不绑评审 skill；只读委派读上一 Stage Handoff。使用者点名岗位 / 多角色时才叠加 `$role-based-reviewer`。

Simple 默认推荐 `human`。`human` 的完成标准：使用者在本会话明确接受方案。

派出时 Frozen Input 含：方案路径、评审范围、通过标准。受派方不得问「方案是什么」。不过本 Stage 不得 apply、不得改代码。

完成标准：通过 / 要改方案（回到定方案）已写入 spine。

## 实现 `implement`

必须派出。不允许 `human`。

Frozen Input 含：已通过的方案路径、Track 绑定的实施 skill、不做清单。工作树不干净先在本会话问。

完成标准：实施 Handoff 或工作区变更与方案对应；`$agent-roster` 返回 `completed`（失败则按 roster 分类后回到本会话）。

## 代码评审 `code-review`

Optional Stage。实现结束后在本会话问做不做。Simple 默认跳过；Medium / Complex 默认建议做。跳过：spine 写 `skipped`，不跑脚本。

选做则必须派出，不允许 `human`。范围门在本会话走 `$dotf-code-review` 的确认门，结果写入 Frozen Input（`mode` / MR URL / from-to）。受派方执行该 skill，产物进项目 `docs/reviews/`。

`ocr` 的 LLM 用本机已有配置，不是本 Stage 的 Model。Model 是跑该 skill 的 Endpoint。

可写且允许脏工作树。`decision.md` 写明例外。

完成标准：`docs/reviews/{日期}/{change-name}/` 已写入 spine，或本会话确认跳过。

## 收尾 `wrap-up`

是否 archive、是否 `$commit-push` 在本会话决定。可 `human`（只摘要、不派出）。

Medium：`$openspec-archive-change`。Complex：归档 `{task}-driver`。Simple 无 archive。

完成标准：约定的收尾动作已完成或明确跳过；spine 状态为 `done`。
