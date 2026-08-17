# Archive 阶段

执行前读根 `SKILL.md` 与 `safety.md`（ARCH-1、PROXY-1）。顺序固定：预检 → 外部归档 → 落盘。

## 1. 预检

`resolve <id> --command task-archive` 后跑 `archive <id> --dry-run`。

- 退出码 2：CLI 给出每个 gate 的 `affected` 与 `exact_action`（`--allow-remaining`、`--allow-unchecked-acceptance`、可重复的 `--allow-dirty <repo>`）。原样报告并等用户确认，**只传用户确认的那个 flag**，不自行组合或扩大范围。
- 退出码 1：change 找不到、README 表格 malformed 等硬失败，任何 flag 都不能绕过，修好再来。
- 退出码 0：读 `pending_openspec_archive`，那是还需要外部归档的 change。

## 2. 外部归档

`openspec-*` skill 由目标仓自己跑 `openspec init --tools <agent>` 生成，**不能假定存在**；归档统一直调 `openspec` CLI。绑定契约不变：在该 change 的 `planning_root` 下执行，且显式传 change name——CLI 只认 cwd 最近的 `openspec/`，缺任一项会写错位置或反问选 change。

对每个 pending change：

1. `openspec validate --strict --type change <name>`，失败就停止并原样报告，task 保持 active。
2. 判定 delta 同步状态：把 `openspec/changes/<name>/specs/<capability>/spec.md` 中 `## ADDED / MODIFIED / REMOVED / RENAMED Requirements` 下的每条 `### Requirement:` 标题**与正文**，对照主 spec `openspec/specs/<capability>/spec.md`。
3. 按判定结果选命令：

| 判定 | 命令 |
|------|------|
| 主 spec 不含这些 requirement（正常情况） | `openspec archive --yes <name>` |
| 每条都已在主 spec 且正文逐字相同 | `openspec archive --yes --skip-specs <name>` |
| 只同步了一部分，或标题相同但正文不同 | 停止，原样报告差异，等用户决定 |

`--skip-specs` 仅用于第二种判定，且必须在报告里写明「主 spec 已预同步，跳过 spec 更新」。这是本文档授权的动作，不属于 `SKILL.md` 说的「自行扩大授权范围」——那条约束的对象是 taskctl 的 gate flag，不是 openspec CLI 参数。

任一 change 失败立即停止。

### 失败与续跑

`openspec archive` 是原子的，失败时打印 `Aborted. No files were changed.`，不会留下部分落盘。

| 症状 | 含义 | 处理 |
|------|------|------|
| `ADDED failed for header "..." - already exists` | 主 spec 已被提前同步，第 2 步判定漏做或漏判 | 回第 2 步逐条比对正文，确认逐字相同后改用 `--skip-specs` |
| 报 requirement 找不到、正文对不上 | delta 与主 spec 不同源 | 停止报告，**不要**用 `--skip-specs` 掩盖 |
| 归档若干个后中途失败 | 部分成功 | 修掉原因后直接重跑本节；CLI 按 `YYYY-MM-DD-<change>` 整名识别已归档的 change，不重复也不丢 |

主 spec 被手工预同步（典型是有人在合并前先「sync specs」）会让整批 change 落入第二种判定。这只影响归档命令的选择，不改变 gate 结论。

若 task 有 `design/` 且设计需要正式落地，此时按 README 记录的落点晋升到已列为 `必须` 的目标仓；不要往 `建议` / `排除` 仓猜落点。

## 3. 落盘

所有 change 都已归档后跑 `archive <id>`（带上第 1 步确认过的 flag）。CLI 会：

- 再校验一遍 gate，change 仍 active 就以 `openspec_not_archived` 硬失败；
- 写 `changes.md`（交付仓库与分支、change 状态、门禁覆盖）；
- 把 status 改为 `archived`，移动目录到 `tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`，重建 `INDEX.md`。

最后向用户汇报归档路径、各 change 状态、交付分支和用到的门禁覆盖。

归档后还要继续做，用 `restore <id>` 恢复为 active，不要手动移目录。
