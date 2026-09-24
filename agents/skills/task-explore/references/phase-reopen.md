# reopen 阶段

进入本阶段后执行；未读完不得搬动任何目录。

把已归档的探索任务搬回 `tasks/ongoing/{task-name}`，或对 `handed-off` 任务撤回交接。两种形态动作不同：前者搬整树，后者只改状态，目录不动。

## 定位

1. 未指定名字：`archived` 任务用 INDEX 的 Archived 表列出请用户选；`handed-off` 任务在 Ongoing 表中点名。指定了则用该名字。
2. `status: archived` → 在 `tasks/archive/` 下按任务名定位，含 `archive/{yyyy-mm-dd}/{parent}/{sub}` 的嵌套位置；`status: handed-off` → 在 `ongoing/` 定位。找不到就报告并停止，不猜路径。
3. 状态以 `TASK.md` 的 `status` 为准，不按目录位置猜。INDEX 与目录不一致时先按 `SKILL.md` 索引规则重建 INDEX，再定位。

## 门禁（按序；任一不过即停）

1. **目标路径**（仅 `archived`）：计算 `tasks/ongoing/{task-name}`。**目标已存在则停止并询问，禁止覆盖；此时不得改 `TASK.md`、不得移动目录、不得改 INDEX。** 冲突时由用户定夺改走 `resume` 还是换名。
2. **子任务名撞车**：整树搬回前扫 `ongoing/` 全树，若某个 `{sub}` 与别的父任务的子任务重名（driver 名 `{sub}-driver` 会撞），列出冲突双方，问用户改子任务名还是换父任务名；未定不搬。
3. **driver 现状**：曾 `handed-off` 的任务先报告 `{task-name}-driver` 是否仍在、openspec 侧进度或已归档状态，读不到写「进度未知」，不得当作已完成。撤回交接时提醒：driver 已产出的 change 不自动删除，保留或走 openspec 归档由用户定。
4. **确认**：拿到用户「确认 reopen」的明确答复才动，只给任务名不算确认。多条门禁同时命中时合并成一次确认，不逐条往返。

## 步骤

1. `archived` 任务：`status` 改回 `ongoing`，保留 `archived: YYYY-MM-DD` 作为历史，加 `reopened: YYYY-MM-DD`，更新 `updated`。已有决策、交接、归档记录一律不删不改写。
2. `archived` 任务：`mkdir -p tasks/ongoing`，把整个 `{taskRoot}`（含子任务树）**移动**回 `tasks/ongoing/{task-name}`。树内已 `handed-off` 或已 `archived` 的子任务保持原状态，不自动复活。
3. `handed-off` 任务：**不搬目录**，只把 `status` 改回 `ongoing`，加 `reopened: YYYY-MM-DD`，并在交接小节追加「撤回交接：[原因]（YYYY-MM-DD）」。driver 及其 change 不删。
4. 更新 INDEX：`archived` 任务把该行从 Archived 移回 Ongoing（更新日取 reopen 日，路径改回 `ongoing/{task-name}/`，子任务行批量改回 `ongoing/{parent}/{sub}/`）；`handed-off` 任务的行留在 Ongoing，但**去掉 `→ {task-name}-driver` 尾注** —— 它已不是 handed-off，留着会让索引谎报。父行聚合描述改回与子任务当前状态一致。无 INDEX 则按目录重建。
5. 搬完自证：旧路径已不存在、`tasks/ongoing/{task-name}/TASK.md` 可读、INDEX 该行路径实际存在。不一致即报告漂移，按 `SKILL.md` 索引规则重建。
6. 绑定该探索任务（`reopen` 完成前 `{taskRoot}` 仍在 archive），用短摘要恢复上下文：**目标 / 当时结论 / 归档原因 / 撤回交接原因 / 建议下一步**，然后等用户。

`SUMMARY.md` 随树搬回，作为历史叙述原样保留、不改写；下次归档按 `references/phase-archive.md` 续写新增时间线。批量 reopen 不在本阶段范围：逐个走完整门禁。
