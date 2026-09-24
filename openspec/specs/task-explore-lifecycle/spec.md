## Purpose

定义 task-explore 探索任务的生命周期状态机：各状态的语义、handoff 与 archive 解耦后的可见性规则，以及任务目录的写盘边界，保证任务在整个交付期内对用户与后续会话保持可发现、可恢复。
## Requirements
### Requirement: handoff 只交接不归档
`handoff` 阶段 SHALL 只完成向 taskflow 的交接：在 `TASK.md` 写交接小节、桥接 `{task-name}-driver`。它 MUST NOT 修改 `status: archived`、MUST NOT 移动任务目录、MUST NOT 清除会话绑定、MUST NOT 把任务行从 INDEX 的 Ongoing 表移走。`TASK.md` 的 `status` SHALL 记为 `handed-off`，任务目录保留在 `tasks/ongoing/{task-name}`。

#### Scenario: handoff 成功后任务仍在 ongoing
- **WHEN** `handoff` 完成且 driver 已存在
- **THEN** `TASK.md` 的 `status` 为 `handed-off` 且含 `handed-off` 日期与 `driver` 名
- **THEN** 任务目录仍在 `tasks/ongoing/{task-name}/`，未被移动
- **THEN** INDEX 的 Ongoing 表仍列该任务，一句话以 `→ {task-name}-driver` 结尾

#### Scenario: driver 未就绪时不进入 handed-off
- **WHEN** taskflow / openspec 不可用或 planning root 无法确定
- **THEN** `handoff` SHALL 停止并保持任务在 `ongoing/`，`status` 不变，已写交接段可保留

### Requirement: handed-off 任务保持只读可见
状态为 `handed-off` 的任务 SHALL 继续出现在 INDEX 与 `resume`/绑定流程的任务列表中；交付进度以 taskflow checkbox 为准，任务文档内 MUST NOT 再勾交付进度。对 handed-off 任务再执行 `handoff` SHALL 视为重复交接，报告 driver 路径并保持状态不变。

#### Scenario: 新会话仍能看到 handed-off 任务
- **WHEN** 无任务上下文的会话触发 task-explore 绑定流程
- **THEN** Ongoing 列表 SHALL 包含 handed-off 任务及其 `→ {task}-driver` 一句话
- **THEN** 会话可以 `resume` 该任务查看方案、决策与交接记录（只读交付进度）

#### Scenario: 归档后的 driver 不自动改变探索任务状态
- **WHEN** `{task-name}-driver` 在 openspec 侧完成并归档
- **THEN** 探索任务的 `status` 保持 `handed-off`，除非用户点名 `archive`

### Requirement: archive 语义为探索任务真正关闭
`archive` 阶段 SHALL 仅用于「不交付且确认关闭」或「handed-off 后确认无需回溯」的探索任务，且 MUST 拿到用户「确认关闭」的明确答复 —— 仅提供任务名不构成确认。目标路径 `tasks/archive/{yyyy-mm-dd}/{task-name}` 已存在时 MUST 停止并询问，禁止覆盖。曾 `handed-off` 的任务在搬动前 MUST 先按 `save` 把进展写回 `TASK.md`；纯 `ongoing` 任务用户坚持可跳过，但 MUST 在归档记录注明。handed-off 任务归档后，若其 driver 可能仍在运行，`archive` 输出 SHALL 给出警告。

#### Scenario: 只给任务名不搬
- **WHEN** 用户说「归档 X」但尚未对门禁结果给出「确认关闭」答复
- **THEN** `archive` SHALL 汇总门禁结果请求确认，确认前不改 `TASK.md`、不移动目录、不改 INDEX

#### Scenario: handed-off 任务未落盘不搬
- **WHEN** 待归档任务 `status` 为 `handed-off` 且本轮有未写回的进展
- **THEN** `archive` MUST 先按 `save` 写回 `TASK.md` 再搬，不接受按现状归档

#### Scenario: handed-off 任务点名归档
- **WHEN** 用户对 handed-off 任务执行 `archive`
- **THEN** 目录移至 `tasks/archive/{yyyy-mm-dd}/{task-name}`，`status` 改 `archived`，INDEX 行移入 Archived
- **THEN** 输出警告 `{task-name}-driver` 可能仍在，提示确认 driver 已完成

#### Scenario: 归档目标已存在
- **WHEN** 计算出的归档目标路径已存在
- **THEN** `archive` MUST 停止并询问，不得改 `TASK.md`、不得移动目录、不得改 INDEX

### Requirement: 任务产物写盘边界
单任务产物 MUST 只写当前任务目录（`{taskRoot}` 及其 `design/`、`glossary.md`、`SUMMARY.md`）；`tasks/INDEX.md` 是唯一允许的 `tasks/` 根级任务文件。评审、方案、决策与归档总结类产物 MUST NOT 写入 `tasks/` 根级新目录（如 `tasks/reviews/`）或仓库 `docs/`、根 `CONTEXT.md`。

#### Scenario: 评审意见落盘
- **WHEN** plan-review 产生评审意见或委派 agent 返回评审文本
- **THEN** 产物 SHALL 写入绑定的 `{taskRoot}`（如 `design/review-<slug>.md`）
- **THEN** MUST NOT 创建 `tasks/` 根级新目录

#### Scenario: 归档总结落盘
- **WHEN** `archive` 生成人读总结
- **THEN** 文件 SHALL 为 `{taskRoot}/SUMMARY.md`，随任务整树进档案
- **THEN** MUST NOT 写到 `tasks/` 根级或仓库 `docs/`

#### Scenario: 发现根级目录漂移
- **WHEN** 发现 `tasks/` 根级存在 INDEX 与任务目录之外的文件或目录
- **THEN** 恢复/重建流程 SHALL 只认 `TASK.md` 目录树，并提示该漂移目录需用户处置

### Requirement: decide 未决问题显式确认
`decide` 阶段把未决问题列为「可带进实现的未决」并以默认值带入时，MUST 逐条向用户确认；未获确认的未决项 MUST 保持开放，不得静默冻结为默认值。

#### Scenario: 未决问题全部确认后才可冻结
- **WHEN** `decide` 存在带默认值的未决问题
- **THEN** 输出逐条清单请用户确认或改值
- **THEN** 全部得到答复后才写入决策小节并提示 `handoff`

#### Scenario: 用户拒绝默认值
- **WHEN** 用户对某条未决拒绝推荐默认值
- **THEN** 该项保持开放并回到 `explore` / `design` / `chat`，决策小节不得收录该条

### Requirement: handoff 目标自动推断
`handoff` 触发时 SHALL 按绑定对象自动推断交接目标，不得要求用户逐项指定：绑定子任务 → 交接该子任务；绑定父任务 → 父为纯伞不可交接，自动扫描并批量交接所有「已 `decide` 且未交接」的子任务；就绪子任务为零时 MUST 打断并报告各子任务所缺条件。未 `decide` 的子任务 MUST NOT 阻塞其它子任务的交接。

#### Scenario: 绑定子任务直接交接
- **WHEN** 会话绑定子任务 `{parent}/{sub}` 且用户点名 `handoff`
- **THEN** 直接交接该子任务，建 `{sub}-driver`，不询问其它子任务

#### Scenario: 绑定父任务批量交接
- **WHEN** 会话绑定父任务且存在 ≥1 个「已 decide 未交接」的子任务
- **THEN** 全部就绪子任务被自动逐个交接，每个建独立 `{sub}-driver`，无需逐项确认
- **THEN** 输出每个子任务的交接结果（driver 路径或失败原因）

#### Scenario: 没有就绪子任务
- **WHEN** 会话绑定父任务点名 `handoff`，但没有任何「已 decide 未交接」的子任务
- **THEN** `handoff` MUST 停止并报告每个子任务的状态与所缺条件（未 decide / 已 handed-off）
- **THEN** MUST NOT 创建任何 driver

#### Scenario: 部分子任务未 decide 不阻塞
- **WHEN** 批量交接时部分子任务尚未 decide
- **THEN** 未 decide 的子任务被跳过且列入报告，已就绪的照常交接

### Requirement: 批量交接失败即停
批量交接多个子任务时，任一子任务交接失败 MUST 立即停止剩余交接，已成功的不回滚，失败原因写入报告。

#### Scenario: 中途失败
- **WHEN** 批量交接第 N 个子任务失败（如 openspec / taskflow 不可用）
- **THEN** 停止后续子任务的交接，已完成的 driver 保留，报告失败子任务与原因
- **THEN** 由用户决定重试或降级，不自动续跑

### Requirement: 多次 handoff 的父级聚合
每个子任务 SHALL 拥有独立 driver `{sub}-driver`（`{sub}` 全局唯一），MUST NOT 为父任务建 driver。父任务的 `TASK.md` 登记表 SHALL 记录每个子任务的状态与其 driver 指针；INDEX 父任务行的一句话 SHALL 聚合子任务状态（如「3 子任务：2 已交接、1 设计中」）。

#### Scenario: 父任务登记表聚合
- **WHEN** 任一子任务完成交接
- **THEN** 父 `TASK.md` 登记表更新该子任务行：状态 `handed-off` + driver 路径
- **THEN** INDEX 父行一句话反映子任务聚合状态

#### Scenario: 父任务永不建 driver
- **WHEN** 用户点名父任务 `handoff` 且父任务无子任务
- **THEN** 停止并提示 `split` 拆分或改走 `new`，MUST NOT 建 `{parent}-driver`

### Requirement: 父任务纯伞与归档门禁
父任务（有子任务的任务）SHALL 保持 `status: ongoing`，自身无独立交付进度，MUST NOT `decide` 具体方案（仅可冻结范围、非目标与拆分原则）、MUST NOT `handoff`。父任务 `archive` 的门禁 SHALL 为：所有子任务 `status` ∈ {`handed-off`, `archived`}，且用户确认无需回溯。

#### Scenario: 子任务全部交接后归档父任务
- **WHEN** 所有子任务均为 `handed-off` 或 `archived`，用户点名父任务 `archive`
- **THEN** 归档父任务（含整棵子任务树搬目录），INDEX 行移入 Archived

#### Scenario: 仍有探索中子任务时拒绝归档
- **WHEN** 任一子任务仍为 `ongoing`，用户点名父任务 `archive`
- **THEN** 停止并列出未结子任务，不得归档

### Requirement: decide 版本化与重新决策
同一探索任务 MAY 多次 `decide`：新决策 SHALL 追加写入决策小节并编号，被取代的旧决策 SHALL 标注「被 D-n 取代」而非删除。`status` 为 `handed-off` 的任务 MUST 先 `reopen` 撤回交接（`status` 回到 `ongoing`）才可重新 `decide`；改动较小时 SHOULD 优先直接修订 driver 的 proposal 而非撤回交接。父任务的 `decide` MUST 限于范围、非目标与拆分原则，具体方案属各子任务的 `decide`。

#### Scenario: 重复 decide 追加版本
- **WHEN** 已存在 D1–D19 的任务再次 `decide`
- **THEN** 新决策以新编号追加，被推翻的旧条目保留并标注「被 D-n 取代」

#### Scenario: handed-off 任务重新 decide
- **WHEN** `handed-off` 任务需要重新决策
- **THEN** 必须先 `reopen` 撤回交接（driver 可能仍在，输出警告），`status` 回到 `ongoing` 后方可 `decide`
- **THEN** 决策变更后须重新 `handoff`

#### Scenario: 父任务 decide 仅限拆分层面
- **WHEN** 父任务 `decide`
- **THEN** 冻结内容只含范围、非目标与拆分原则，不含任何子任务的具体实现方案

### Requirement: archive 关闭留痕
`archive` MUST 在 `TASK.md` 写 **归档** 小节，含五要素：本次结论（无结论时写 `未得出结论`，不留空）、关闭原因（`已交付` / `放弃` / `被 {task-name} 取代` / `其它` + 一句话）、未决清点结果、交付侧现状、入链处理结果。关闭原因 MUST 取自用户回答，不得代为推断。`archived` 日期 SHALL 在 `TASK.md` 元信息、归档目录名、INDEX 归档日三处一致。

#### Scenario: 三种结局可区分
- **WHEN** 后续会话或 `reopen` 读取一份 archived 任务
- **THEN** 从 **归档** 小节即可判断它是做完了、放弃了，还是被别的任务取代

#### Scenario: 日期不一致视为未完成归档
- **WHEN** 元信息 `archived` 与目录名或 INDEX 归档日不同
- **THEN** `archive` SHALL 修正为同一个 `{yyyy-mm-dd}` 后再报告完成

### Requirement: archive 前清点未决与交付侧进度
`archive` SHALL 在搬动前清点 `TASK.md` 的未决问题与下一步，并向用户报告条数与首条内容；用户可选择「随任务关闭」或「先补结论」。未决项 MUST NOT 被要求清零，但关闭结果 MUST 记入归档记录。曾 `handed-off` 的任务 SHALL 读取 `{task-name}-driver` 在 openspec 侧的进度（checkbox 与 change 归档状态）并报告「已完成 X/Y」；读不到时 MUST 报「进度未知」且不得当作已完成。清点结果只写归档记录，MUST NOT 回写 `TASK.md` 的进度字段，也不勾 taskflow 的框。

#### Scenario: 带着未决关闭
- **WHEN** 任务有 3 条未勾未决且用户确认随任务关闭
- **THEN** 归档照常进行，归档记录写「3 条未决随归档关闭」，未决项原样保留

#### Scenario: 交付进度读不到
- **WHEN** driver 路径失效或 openspec 侧无进度可查
- **THEN** 报告「进度未知」并等用户确认，MUST NOT 报成已完成

### Requirement: archive 入链检查与搬后自证
`archive` SHALL 在搬动前搜索 `tasks/` 内指向 `{taskRoot}` 旧路径的链接（父↔子互链、`design/` 与评审稿互链），命中则列出并询问是否改指新归档路径；用户拒绝时 SHALL 保留断链并记入归档记录。搬动后 `archive` MUST 自证：旧路径已不存在、新路径下 `TASK.md` 与 `SUMMARY.md` 可读、INDEX 每条归档路径实际存在；不一致时 SHALL 报告漂移并按索引规则重建 INDEX，不得静默。

#### Scenario: 断链经确认后保留
- **WHEN** 父 `TASK.md` 链接到子任务旧路径且用户拒绝改链
- **THEN** 归档完成，归档记录写「保留断链」

#### Scenario: 移动后索引指空
- **WHEN** 自证发现 INDEX 某归档路径不存在
- **THEN** 按 `ongoing/` 与 `archive/` 下的 `TASK.md` 重建 INDEX 后再报告归档完成

### Requirement: archive 产出人读时间线总结
`archive` MUST 写 `{taskRoot}/SUMMARY.md`：面向人的叙述性总结，篇幅不超过约 40 行，主干为 `YYYY-MM-DD — 做了什么 → 得到什么结论` 的时间线（同类合并），并含「关键决策」「交付」（driver、进度、主要落地位置）「遗留」段落。素材限于 `TASK.md` 的进展/决策/交接、`design/` 各稿与评审意见、driver 侧进度；读不到 MUST 写「未记录」而不得编造。总结 MUST 在搬动目录前交给用户过目并按反馈修订。`TASK.md` 的归档小节 SHALL 只留结论与指针，叙述以 SUMMARY 为唯一真相。

#### Scenario: 半年后快速了解任务
- **WHEN** 后来者打开 `tasks/archive/{yyyy-mm-dd}/{task-name}/SUMMARY.md`
- **THEN** 一屏内看到该任务要解决的问题、时间线上的关键结论、最终交付落点与遗留问题

#### Scenario: 父任务总结不复述子任务
- **WHEN** 父任务归档生成总结
- **THEN** 只写整体脉络与各子任务指针，子任务细节留在各自的 `SUMMARY.md`

### Requirement: 批量归档合并确认且失败不回滚
一次点名多个探索任务归档时，`archive` SHALL 逐个执行完整门禁，但把各任务的门禁结果一次性汇总请求确认（每任务一行：未结子任务、未决条数、driver 进度、目标路径冲突）。目标路径冲突或子任务未结的任务 SHALL 先剔除并单独报告，不阻塞其余；搬运中途失败 MUST 停止，已搬的不回滚，并报告已归档与未归档清单。

#### Scenario: 一个冲突不阻塞其余
- **WHEN** 批量归档 3 个任务，其中 1 个目标路径已存在
- **THEN** 冲突任务被剔除并单独报告，其余 2 个在用户确认后照常归档

### Requirement: reopen 以状态为权威并修正索引
`reopen` MUST 以 `TASK.md` 的 `status` 判定形态（`archived` 搬整树 / `handed-off` 只改状态不搬目录），不按目录位置猜；INDEX 与目录不一致时 SHALL 先重建 INDEX 再定位。目标 `tasks/ongoing/{task-name}` 已存在时 MUST 停止并询问，禁止覆盖，且此时不得改 `TASK.md`、不得移动目录、不得改 INDEX。整树搬回前 SHALL 扫描 `ongoing/` 检查 `{sub}` 是否与别的父任务的子任务重名（`{sub}-driver` 会撞），冲突未定夺不搬。`status` 改回 `ongoing` 时 MUST 保留 `archived: YYYY-MM-DD` 作为历史并加 `reopened: YYYY-MM-DD`，已有决策/交接/归档记录不得删除或改写。撤回 `handed-off` 后 INDEX 行 SHALL 留在 Ongoing 但 MUST 去掉 `→ {task-name}-driver` 尾注。树内已 `handed-off` / 已 `archived` 的子任务保持原状态，driver 及其 change MUST NOT 被删除。`SUMMARY.md` 随树搬回且不改写，下次归档续写。

#### Scenario: 撤回交接后索引不再谎报
- **WHEN** handed-off 任务被 `reopen` 撤回交接
- **THEN** `status` 回 `ongoing`、目录不动，INDEX 该行去掉 `→ {task-name}-driver` 尾注

#### Scenario: 子任务名与别的父冲突
- **WHEN** 整树搬回时某 `{sub}` 已在别的父任务下存在
- **THEN** `reopen` 列出冲突双方并请用户改名，未定夺前不移动目录

#### Scenario: reopen 后再归档
- **WHEN** 任务 `reopen` 后再次 `archive`
- **THEN** 原 `SUMMARY.md` 保留，按 archive 规则续写新增时间线并更新结局，不整篇重写

