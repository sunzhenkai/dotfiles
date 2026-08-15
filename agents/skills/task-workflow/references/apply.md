# Apply 阶段

执行前读根 `SKILL.md`，并遵守 `safety.md` 的 RES-1/3、CHECKOUT-1/2/3、APPLY-1/2/3、MUT-1。

## 流程

1. 运行 `resolve <id> --command task-apply`。显式命中 archived task 时，报告后运行 `restore <id> --status in_progress`，再 resolve；不得对其他命令静默恢复。
2. 首次实现写入前运行：
   ```bash
   python3 <skill>/scripts/taskctl.py prepare-branches \
     --slug <slug> --from-task <id>
   ```
   只处理必须仓；`needs_user_confirm` 时停止，禁止自行 stash/reset/force checkout。命令会持久化真实 checkout/worktree/branch/base。
3. 运行 `execution-context <id>`，以 JSON 的 `targets`、`scope`、`apply_schedule`、`progress_markdown` 为准，不从 cwd 猜 planning root 或 checkout。无 OpenSpec target 时停止并建议 propose。
4. 开始或续作时调用一次：
   ```bash
   python3 <skill>/scripts/taskctl.py advance <id> \
     --phase implementing --change <change> --current-task "<checkbox 原文>"
   ```
5. 实施 `apply_schedule.next`。每完成一个 OpenSpec checkbox，先在对应 `tasks.md` 勾选，再调用一次 `advance --phase implementing --completed "..."`。
6. 读取同一响应：
   - `result=next`：同一轮继续 `next`，不得只做阶段总结。
   - `result=deferred_only`：确无 runnable 项，汇总 deferred 后才可暂停。
   - `result=done`：进入验证并最终记录 done。

## Deferred

当前项因手工验证、环境暂缺或局部依赖不可执行，但其他项可继续时：

```bash
python3 <skill>/scripts/taskctl.py advance <id> \
  --phase implementing --change <change> --current-task "<原文>" \
  --defer-current "<具体原因>"
```

保持 checkbox 未勾选。恢复时对同一 change/task 使用 `--resume-current`。只有全局故障或需要用户决策时才用 `--phase blocked --blocker ...`。

## 验证与完成

```bash
python3 <skill>/scripts/taskctl.py advance <id> \
  --phase testing --verification "<命令与结果>"
python3 <skill>/scripts/taskctl.py advance <id> --phase done
```

`--phase done` 仅在所有 OpenSpec checkbox 完成时成功。输出真实 checkout/分支、各 change 进度、runnable/deferred、`progress.md` 路径；全部完成后桥接 `task-archive`。
