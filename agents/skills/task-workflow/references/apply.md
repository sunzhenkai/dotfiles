# Apply 阶段

执行前读根 `SKILL.md`，并遵守 `safety.md` 的 RES-1/3、CHECKOUT-1/2/3/4、APPLY-1/2/3/4/5、MUT-1。

## Checkout 与 execution context

1. 运行 `resolve <id> --command task-apply`。显式命中 archived task 时，报告后运行 `restore <id> --status in_progress`，再 resolve；不得对其他命令静默恢复。
2. 首次实现写入前运行：
   ```bash
   python3 <skill>/scripts/taskctl.py prepare-branches \
     --slug <slug> --from-task <id>
   ```
   只处理必须仓。任一仓 blocked 时整次准备不是成功；已成功仓的 binding 可保留以便重试，但不得为失败仓写 binding。禁止自行 stash/reset/force checkout，也不存在跳过 dirty 必须仓的选项。
3. 运行 `execution-context <id>`。每个 delivery 仓必须有已持久化 binding，且 checkout 必须存在、同源、非 detached HEAD、当前分支等于记录分支；失败时停止，绝不回退 canonical checkout。
4. 以 JSON 的 `targets`、`scope`、`checkout_gate`、`apply_schedule.candidates`、`progress_markdown` 为准。无 OpenSpec target 时停止并建议 propose；非空 OpenSpec `store` 当前不受支持，必须按错误处理。

## 实施与 candidate 依赖检查

开始或续作时调用：

```bash
python3 <skill>/scripts/taskctl.py advance <id> \
  --phase implementing --change <change> --current-task "<checkbox 原文>"
```

`candidates` 只表示“未显式 defer 且 artifact 可读取”，**不表示依赖已经满足**。执行每个 candidate 前，Agent 必须读取 task/design 上下文，检查它是否直接或传递依赖任何 deferred 项：

- 独立 candidate：实施；完成后先勾选对应 `tasks.md`，再 `advance --phase implementing --completed "..."`。仓级测试只写入 `--completed` / `--verification` 文本。
- 依赖 deferred 项：不得实施；对该 checkbox 使用 exact `--change` + `--current-task` 调用 `--defer-current`，reason 必须包含 blocker identity（change 与 checkbox 原文/稳定 ID），然后读取下一个 candidate。
- 当前项因环境/手工验证局部不可执行：保持 checkbox 未勾选并 exact defer；恢复时对同一 change/task 用 `--resume-current`。
- 只有全局故障或需要用户决策时才用 `--phase blocked --blocker ...`。
- exact defer 只针对当前 checkbox。change 级「依赖前置 change」只约束该 change 的集成/验收门，不自动 defer 同 change 其余项或后续 change 的独立项。
- `result=next` 时继续独立 candidate；已 defer 项并行挂起，不得改口等待恢复，也禁止 testing/done。

## Outcome 控制

调用方只依据顶层 `result` 控制流程；候选事实不能覆盖 phase outcome。表中「停」只结束本轮 candidate 调度，不是 task 完成，也不是任何宿主完成信号。只有 `done` 才允许对外宣称完成并桥接 archive：

| result | 行为 |
|--------|------|
| `blocked` | 停本轮调度，`next=null`；即使 candidates 非空也不得继续；保持 `in_progress`，不宣称完成 |
| `next` | 同一轮检查并处理 `next` candidate；已 defer 项保持挂起；禁止 testing/done |
| `deferred_only` | 无独立候选，汇总 deferred 后停本轮调度；保持 `in_progress`，不宣称完成 |
| `validation_required` | checkbox 已耗尽但尚无 fresh final verification，或本轮验证仅 provisional；停本轮调度，不宣称完成 |
| `validation_recorded` | clean delivery branch/HEAD 的最终验证已记录；只进入 done transition，不宣称对外完成 |
| `done` | final done transition 已完成；checkbox 与 fresh verification 均满足；才允许对外宣称完成并桥接 archive |

## 验证与完成

1. 任一 OpenSpec target 仍有 remaining 时禁止 testing/done。`execution-context` ok 只表示 checkout 可用。implementing 期间的仓级测试不是 final verification。
2. 所有 checkbox 完成后，`advance --phase implementing` 返回 `validation_required`，不会返回 done。
3. 先提交/清理全部 delivery checkout，再运行：
   ```bash
   python3 <skill>/scripts/taskctl.py advance <id> \
     --phase testing --verification "<命令与结果>"
   ```
   dirty checkout 上证据仅记为 `provisional`，结果仍是 `validation_required`；全部 clean 时在 `progress.md` 记录每个 delivery checkout、branch、HEAD 的 final snapshot，并返回 `validation_recorded`。
4. 再运行 `advance <id> --phase done`。它会重读当前 branch/HEAD；snapshot 缺失、实现恢复、checkout 变 dirty、切分支或 HEAD 变化均返回 `stale_verification`，必须重新测试。
5. `done` 后桥接 `task-archive`；archive 会再次执行相同 checkout 与 final snapshot 校验。
