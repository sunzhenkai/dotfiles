# Archive 阶段

执行前读根 `SKILL.md` 与 `safety.md`（ARCH-1、PROXY-1）。顺序固定：预检 → 外部归档 → 落盘。

## 1. 预检

`resolve <id> --command task-archive` 后跑 `archive <id> --dry-run`。

- 退出码 2：CLI 给出每个 gate 的 `affected` 与 `exact_action`（`--allow-remaining`、`--allow-unchecked-acceptance`、可重复的 `--allow-dirty <repo>`）。原样报告并等用户确认，**只传用户确认的那个 flag**，不自行组合或扩大范围。
- 退出码 1：change 找不到、README 表格 malformed 等硬失败，任何 flag 都不能绕过，修好再来。
- 退出码 0：读 `pending_openspec_archive`，那是还需要外部归档的 change。

## 2. 外部归档

对每个 pending change，在其 `planning_root` 下：

1. `openspec validate --strict --change <name>`，失败就停止并原样报告，task 保持 active。
2. 按绑定契约（在 `planning_root` 下执行且显式传 change name）委托 `openspec-archive-change`。

任一 change 失败立即停止。重跑 `archive --dry-run` 时 CLI 会按 `YYYY-MM-DD-<change>` 整名识别已归档的 change，部分成功不会丢。

若 task 有 `design/` 且设计需要正式落地，此时按 README 记录的落点晋升到已列为 `必须` 的目标仓；不要往 `建议` / `排除` 仓猜落点。

## 3. 落盘

所有 change 都已归档后跑 `archive <id>`（带上第 1 步确认过的 flag）。CLI 会：

- 再校验一遍 gate，change 仍 active 就以 `openspec_not_archived` 硬失败；
- 写 `changes.md`（交付仓库与分支、change 状态、门禁覆盖）；
- 把 status 改为 `archived`，移动目录到 `tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`，重建 `INDEX.md`。

最后向用户汇报归档路径、各 change 状态、交付分支和用到的门禁覆盖。

归档后还要继续做，用 `restore <id>` 恢复为 active，不要手动移目录。
