# Archive 阶段

执行前读根 `SKILL.md`，并遵守 `safety.md` 的 RES-1/2、ARCH-1/2/3、MUT-1。归档分 Prepare 与 Finalize；不要重新运行 Checkout Gate。

## Prepare

1. resolve 后运行 `execution-context <id>`，使用记录的 checkout、planning root 与剩余 checkbox 原文。
2. 若仍有 checkbox：Agent 逐条说明是验证未完成还是功能未完成并给依据，连同完成数交用户裁决。未确认不得归档；用户明确强行合并后才使用 `--force-merge`。
3. 在各 target 的 planning root 委托 `openspec-archive-change`；任一 archive/spec sync 失败立即停止。
4. 若 task `design/` 存在，按落点表晋升到已列为必须/delivery 的目标仓；晋升造成 delivery dirty 时等待提交/清理后再 Finalize。
5. 运行预检：
   ```bash
   python3 <skill>/scripts/taskctl.py archive <id> --dry-run
   ```
   dry-run 即使尚无 `changes.md` 也可运行，并在 `archive_gate.delivery_summaries` 返回 delivery checkout 的 commits、staged、working-tree 与 untracked 摘要。
6. 根据 summaries 写 `changes.md`，分开记录 Delivery repositories、Planning stores、Task-store mutations、Gate overrides；不得把 planning/task-store dirty 冒充 delivery 未完成。

## Finalize

1. 再运行 `archive <id> --dry-run`。`archive_gate.blocking` 非空时停止；delivery missing、status unavailable、dirty 都 fail closed。
2. `non_blocking_dirty` / `non_blocking_diagnostics` 只报告 planning/task-store 状态；同仓含 delivery 角色时仍必须 clean。
3. delivery dirty 确需覆盖时先取得用户明确确认，再逐仓传 `--allow-dirty-checkout <repo>`；它不能覆盖 missing/invalid/status unavailable。
4. 预检通过后运行 `archive <id>`。CLI 校验 OpenSpec、验收、验证证据和 delivery clean，然后原子更新 status、移动 task、写 INDEX；失败自动回滚。
5. 输出 OpenSpec/设计晋升结果、delivery gate、非阻塞诊断和最终归档路径。
