# handoff 阶段

进入本阶段后执行。未绑定则先回到 `SKILL.md` 的绑定规则。

把 **探索任务**（`tasks/ongoing/{task-name}`）交接给 **taskflow 任务**（`{task-name}-driver`）。交付进度之后只认 taskflow checkbox。本阶段 **不写实现代码**，不发明 openspec 等价命令。交接后探索任务转入 `handed-off`：**不归档、不搬目录、不清绑定**。

## 目标推断（自动）

按绑定对象确定交接目标，无需用户逐项指定：

- 绑定子任务 → 交接该子任务（driver 名 `{sub}-driver`）。
- 绑定父任务 → 父是纯伞不可交接；自动扫描其子任务，批量交接所有「已 `decide` 且未 `handed-off`」的子任务。未 `decide` 的子任务跳过并列入报告，不阻塞其余。
- 父任务无子任务 → 停止，提示 `split` 拆分或 `new` 另建任务；**不得建 `{parent}-driver`**。
- 批量交接中任一子任务失败 → **立即停止**剩余交接；已成功的不回滚，失败原因写入报告，由用户决定重试或降级。

## 单任务交接门禁

1. 该任务 `TASK.md` **决策** 小节已写明采纳方案。没有则打断，先 `decide`。（父任务批量交接时逐个子任务检查；不满足的子任务按「跳过」处理并列入报告，不整体打断。）
2. driver change 名 = 任务 slug + `-driver`（子任务为 `{sub}-driver`），不得从描述重新归纳成别的名字。在同一 planning root 下检查 driver 是否已存在：已存在则不要新建，把现有路径写入交接段，视为脚手架已就绪。
3. 任务已是 `handed-off` 且 driver 已存在：报告 driver 路径并保持状态不变，不重复交接。

## 步骤

1. 有未写入进展则先按 `save` 写回。
2. 在 `TASK.md` 写 **交接** 小节：driver 名、采纳方案、`design/` 指针、可带进实现的未决。
3. 读取并遵循 `taskflow` 的脚手架（`taskflow-new`）。`--goal` 用目标 + 已采纳方案，不要只丢一句含糊摘要。
4. 按 taskflow 写入 driver 的 `.openspec.yaml`（`skip_specs: true`）和 `proposal.md`（含逐字 Driver 协议）。**不要写 `tasks.md`。**
5. taskflow / openspec 不可用，或无法确定 planning root：停下报告可选项，**保持探索任务在 `ongoing/`、状态不变**，已写的交接段可保留。
6. 收尾：`TASK.md` 的 `status` 改为 `handed-off`，写入 `handed-off` 日期与 `driver` 名；INDEX 行一句话更新为 `已交接：… → {task-name}-driver`（**行留在 Ongoing 表**）；保留会话绑定。
7. 桥接 stock `openspec-propose`（方案已定时选继续已有 change；未定时先 `openspec-explore`）。之后不要在 `tasks/` 里勾交付进度。

## 父任务批量交接

1. 扫描子任务，筛出「已 decide 未 handed-off」集合；为空则打断，报告每个子任务的状态与所缺条件。
2. 按上方单任务流程逐个交接；每个子任务独立 driver `{sub}-driver`，父任务**不建** driver。任一失败即停（见「目标推断」）。
3. 全部完成后：父 `TASK.md` 的子任务登记表逐行更新状态与 driver 路径；INDEX 父行一句话聚合子任务状态（如「3 子任务：2 已交接、1 设计中」）；报告每个子任务的交接结果。
