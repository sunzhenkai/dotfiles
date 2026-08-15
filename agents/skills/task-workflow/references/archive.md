# Archive 阶段

执行前读根 `SKILL.md`，并遵守 `safety.md` 的 RES-1/2、ARCH-1/2/3/4、MUT-1。归档固定为 Initial preflight → External actions → Final preflight → task finalize；外部写入不伪装成 task-store 原子事务。

## 1. Initial preflight（任何外部写入前）

1. `resolve <id> --command task-archive` 后运行：
   ```bash
   python3 <skill>/scripts/taskctl.py archive <id> --dry-run
   ```
2. CLI 先校验 catalog、operational tables、OpenSpec identity/status、delivery binding/repository/branch/status、验收结构和最终验证。`result=initial_preflight` 时读取 `target_states`、`external_actions` 与 `archive_gate.delivery_summaries`；此调用不得归档 change、晋升 design 或改写 task。
3. target 状态只认 `active`、`uniquely_archived`、`archived_incomplete`、`missing`、`ambiguous`。active 且 checkbox 完成表示待执行 archive action；uniquely archived 表示重试时已完成。missing/ambiguous/status unavailable、invalid/missing checkout、branch mismatch、malformed data 均为 code 1，任何 override 都不能继续。
4. remaining、unchecked acceptance、missing/stale verification、dirty delivery repo 均由 CLI 以 code 2 返回 `affected` 与 `exact_action`。Agent 原样报告并等待明确确认；只传用户确认的精确 flag，不自行组合或扩大范围。

## 2. External actions（可恢复、逐项执行）

1. 按 `external_actions` 执行 `state=pending` 项：在每个 target 的 `planning_root` 委托 `openspec-archive-change`；已 `completed` 的 target 只核对，不重复归档。任一 target 失败立即停止，task 保持 active。
2. 若列出 `promote_design`，按 task design 的归档落点晋升到已列为 delivery 的目标仓；不向 reference/planning-only 仓猜测落点。
3. 根据 delivery summaries 和实际外部结果写 `changes.md`，分开记录 Delivery repositories、Planning stores、Task-store mutations、External results、Gate Overrides。不得创建额外 archive state 文件。
4. 重试时再次运行 initial preflight；CLI 从 active/archive 实际路径识别已完成 target，遇到 missing/ambiguous 停止，不能把部分成功当作丢失。

## 3. Final preflight 与 finalize

1. 外部动作和 `changes.md` 完成后再次运行 `archive <id> --dry-run`；必须得到 `result=final_preflight`。active target 或缺失 `changes.md` 均不可 finalize。
2. 外部操作新产生的 delivery dirty、HEAD/branch 变化或 stale verification 会在移动 task 前阻断。planning/task_store dirty 仅列入 `non_blocking_*`；同仓具有 delivery role 时仍按 delivery 门禁处理。
3. 若 CLI 返回 code 2，逐项取得用户确认并按 exact action 重跑。允许的 flag 仅为：`--force-merge`、`--allow-unchecked-acceptance`、`--allow-missing-verification`、可重复的 `--allow-dirty-checkout <exact-repo>`。
4. final preflight 通过后以相同精确 flags 运行 `archive <id>`。CLI 在移动前把每项授权写入 `changes.md` 的 `## Gate Overrides`，再原子更新 status、移动 task、写 INDEX；task-store 失败走统一 rollback 报告。
5. 输出 target 状态与外部结果、delivery gate、Gate Overrides、非阻塞诊断和最终归档路径。
