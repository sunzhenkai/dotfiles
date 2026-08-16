# Apply 阶段

执行前读根 `SKILL.md`，并遵守 `safety.md` 的 RES-1/3、CHECKOUT-1/2/3/4、APPLY-1/2/3/4/5/6、MUT-1。本文件是 apply outcome 契约的唯一来源。命令一律写作 `python3 <skill>/scripts/taskctl.py <command> ...`。

## 入口：首次实现与续作

两条入口都先 `resolve <id> --command task-apply`；命中 archived task 时报告后 `restore <id> --status in_progress` 再 resolve。

- **首次实现**：先 `prepare-branches --slug <slug> --from-task <id>`，再 `execution-context <id>`。
- **续作（中断恢复）**：直接 `execution-context <id>`，只在 `resume.prepare_required=true` 时补跑 `prepare-branches`；binding 齐全时不得重跑准备。

`prepare-branches` 只处理必须仓：任一仓 blocked 即整次准备不算成功，已成功仓的 binding 可保留以便重试，但不得为失败仓写 binding；禁止自行 stash/reset/force checkout，也没有跳过 dirty 必须仓的选项。仅落在 canonical planning root 内的未提交改动是 planning 角色诊断（`dirty_role=planning`，附 `planning_action`），准备照常继续；一旦混入其他路径即按 delivery 阻断。

## execution-context 事实

只以 JSON 为准，不从叙述文本反推：

| 字段 | 用途 |
|------|------|
| `checkout_gate` | delivery 仓必须有持久化 binding，且 checkout 存在、同源、非 detached HEAD、分支等于记录分支；失败即停，绝不回退 canonical checkout |
| `openspec_locations` | change 的 canonical planning root 与可读性；change 只在 canonical 侧读写，不随交付分支移动，`readable=false` 时按 `action` 处理，不得改用 delivery 路径 |
| `apply_schedule.groups` | 按 change 分组的进度、候选与暂缓；`candidates` 已按 change 顺序键与 change 内文件顺序排好，可直接顺序取用 |
| `resume` | 上次阶段、上次处理项及其状态、是否需补跑准备、delivery 未提交改动、验证新鲜度 |

`resume.last_item_state` 决定续作起点：`completed` 取下一个候选；`in_flight` 表示该项改了一半，先读 `resume.uncommitted` 的路径判断归属再接着做，**不得**重做；`not_started` 正常开始；`unknown` 必须原样报告并等用户确认，禁止当作 `not_started`。

无 OpenSpec target 时停止并建议 propose。

## 实施与 candidate 依赖检查

开始或续作时调用 `advance <id> --phase implementing --change <change> --current-task "<checkbox 原文>"`。

`candidates` 只表示“未显式 defer 且 artifact 可读取”，**不表示依赖已经满足**。执行每个 candidate 前，Agent 必须读 task/design 上下文，检查它是否直接或传递依赖任何 deferred 项：

- 独立 candidate：实施；完成后先勾选 canonical planning root 下对应 `tasks.md`，再 `advance --phase implementing --completed "..."`。仓级测试只写入 `--completed` / `--verification` 文本。
- 依赖 deferred 项：不得实施；对该 checkbox 用 exact `--change` + `--current-task` 调 `--defer-current`，reason 必须含 blocker identity（change 与 checkbox 原文/稳定 ID），然后取下一个 candidate。
- 当前项因环境/手工验证局部不可执行：保持 checkbox 未勾选并 exact defer；阻塞解除后对同一 change/task 用 `--resume-current` 恢复。
- 只有全局故障或需要用户决策时才用 `--phase blocked --blocker ...`。
- exact defer 只针对当前 checkbox。change 级「依赖前置 change」只约束该 change 的集成/验收门，不自动 defer 同 change 其余项或后续 change 的独立项。

## Outcome 控制

只依据顶层 `result` 控制流程；候选事实不能覆盖 phase outcome。表中「停」只结束本轮 candidate 调度，不是 task 完成，也不是任何宿主完成信号：

| result | 写入 status | 行为 |
|--------|-------------|------|
| `blocked` | `blocked` | 停本轮调度，`next=null`；即使 candidates 非空也不得继续；不宣称完成 |
| `next` | `in_progress` | 同一轮继续处理 `next` candidate；已 defer 项并行挂起，不得改口等待恢复；禁止 testing/done |
| `deferred_only` | `in_progress` | 无独立候选，汇总 deferred 后停本轮调度；不宣称完成 |
| `validation_required` | `in_progress` | checkbox 已耗尽但无 fresh final verification，或本轮验证仅 provisional；停本轮调度，不宣称完成 |
| `validation_recorded` | `in_progress` | clean delivery branch/HEAD 的最终验证已记录；只进入 done transition，不宣称完成 |
| `done` | `in_progress` | final done transition 完成，checkbox 与 fresh verification 均满足；只有 `done` 才允许对外宣称完成并桥接 archive |

## 验证与完成

1. 任一 target 仍有 remaining 时禁止 testing/done。`execution-context` ok 只表示 checkout 可用；implementing 期间的仓级测试不是 final verification。checkbox 全完成后 `advance --phase implementing` 返回 `validation_required`，不会返回 done。
2. 提交或清理全部 delivery checkout：**delivery 提交归本阶段负责**，可委托 skill `commit-push`；planning 产物留在 canonical planning root，不必为通过本门而提交。随后 `advance <id> --phase testing --verification "<命令与结果>"`。delivery 仍有未提交代码时证据仅记 `provisional`，结果仍是 `validation_required`；全部 clean 时在 `progress.md` 记录每个 delivery checkout、branch、HEAD 的 final snapshot 并返回 `validation_recorded`。
3. testing 阶段用同一份证据回填 task README 验收标准：逐条对照勾选，未达成项保持未勾并写明原因，使 archive 的未勾选确认只剩真正未达成项。
4. 再运行 `advance <id> --phase done`。它重读当前 branch/HEAD；snapshot 缺失、实现恢复、checkout 变 dirty、切分支或 HEAD 变化均返回 `stale_verification`，必须重新测试。
5. `done` 后桥接 `task-archive`，archive 会再次执行相同 checkout 与 final snapshot 校验。

## 回路与例外

- 实现中发现 **change 本身有误**（契约写错、拆分不对、缺 spec）：停止该项，用 `advance --phase blocked --blocker "<change>: <问题>"` 记录，桥接 `{{slash:task-propose}} <id>` 修正后再回 apply；不在 apply 里改写 change 语义。
- 跨 task 定位用 `list`（`--archived` 看归档）。apply 期间 status 由 `advance` 写入，只有 apply 之外需人工改状态才用 `set-status`，不得手改 README/INDEX。
