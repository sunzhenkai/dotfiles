# handoff 阶段

进入本阶段后执行。未绑定则先回到 `SKILL.md` 的绑定规则。

把 **探索任务**（`tasks/ongoing/{task-name}`）交接给 **taskflow 任务**（`{task-name}-driver`）。交付进度之后只认 taskflow checkbox。本阶段 **不写实现代码**，不发明 openspec 等价命令。

## 门禁

1. `TASK.md` **决策** 小节已写明采纳方案。没有则打断，先 `decide`。例外：用户本轮明确「按推荐冻结并交接」→ 先做完 `decide` 再继续，不必再问。
2. 计算归档目标 `tasks/archive/{yyyy-mm-dd}/{task-name}`。**目标已存在则停止并询问；此时不得改 TASK.md、不得跑 taskflow-new、不得移动目录。**

## 步骤

1. 有未写入进展则先按 `save` 写回。
2. 在 `TASK.md` 写 **交接** 小节：driver 名 `{task-name}-driver`、采纳方案、`design/` 指针、可带进实现的未决、探索任务将归档的路径。
3. 读取并遵循 `taskflow` 的脚手架（`taskflow-new`）。**`{task}` 必须等于探索任务 slug `{task-name}`**，不得从描述重新归纳成别的名字。`--goal` 用目标 + 已采纳方案，不要只丢一句含糊摘要。
4. 按 taskflow 写入 `{task-name}-driver` 的 `.openspec.yaml`（`skip_specs: true`）和 `proposal.md`（含逐字 Driver 协议）。**不要写 `tasks.md`。**
5. taskflow / openspec 不可用，或无法确定 planning root：停下报告可选项（`dotf agents -c` / `openspec init --tools agents` / 用户指定 root），**保持探索任务在 `ongoing/`**，已写的交接段可保留。
6. `{task-name}-driver` 已存在：不要新建；把现有路径写入交接段，视为脚手架已就绪。
7. **仅当 driver 已存在**（本轮新建或已有）：再按 `archive` 搬家（先确认目标仍不存在 → 改 `status` 为 `archived` 并记下 `handed-off` 与 `driver` → 移动 → 更新 INDEX → 清除探索任务绑定）。
8. 报告：归档路径、`{task-name}-driver` 的 `proposal.md`。桥接 stock `openspec-propose`（方案已定时选继续已有 change；未定时先 `openspec-explore`）。之后不要再在 `tasks/` 里勾交付进度。

INDEX 归档行的一句话以 `→ {task-name}-driver` 结尾，便于检索。
