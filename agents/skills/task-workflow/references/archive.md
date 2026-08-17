# Archive 阶段

执行前读根 `SKILL.md` 与 `safety.md`（ARCH-1、PROXY-1）。顺序固定：预检 → 外部归档 → 落盘。

## 1. 预检

`resolve <id> --command task-archive` 后跑 `archive <id> --dry-run`。

- 退出码 2：**待确认，不是失败**。`confirmations` 里每个 gate 带 `prompt` 与 `affected`。把它们原样报给用户，逐条问「继续归档还是先补完」，拿到明确同意后按 `confirm_command`（`archive <id> --confirmed`）重跑；用户要先补完就停在这里，不得替用户判成「没做完所以不能归档」结束。
- `--confirmed` 一次放行**当次报出的全部 gate**，没有按 gate 拆的 flag，所以只有逐条确认过才能传，实际放行了什么由 CLI 写进 `changes.md` 的门禁覆盖。dirty 只统计真正的业务改动：`tasks/` 台账与本次 change 的 openspec 落点由归档流程自己写，CLI 已排除，不必为它们求放行。
- 退出码 1：change 找不到、README 表格 malformed 等硬失败，确认也绕不过，修好再来。
- 退出码 0：读 `pending_openspec_archive`，那是还需要外部归档的 change。

## 2. 外部归档

`openspec-*` skill 由目标仓自己跑 `openspec init --tools <agent>` 生成，**不能假定存在**；归档统一直调 `openspec` CLI。绑定契约不变：在该 change 的 `planning_root` 下执行，且显式传 change name——CLI 只认 cwd 最近的 `openspec/`，缺任一项会写错位置或反问选 change。

对每个 pending change：

1. `openspec validate --strict --type change <name>`，失败就停止并原样报告，task 保持 active。
2. `openspec archive --yes <name>`，成功就下一个。它是原子的，失败打印 `Aborted. No files were changed.`，不留部分落盘——所以**先跑、报错再分诊**，不要靠预判主 spec 状态决定跑不跑。

### 报错分诊

只在报错后才逐条对照主 spec `openspec/specs/<capability>/spec.md`。每种 delta section 的期望方向不同，只看「正文是否相同」必然误判：

| delta section | 待归档（正常） | 已预同步 |
|---|---|---|
| ADDED | 主 spec 无此条 | 有，正文逐字相同 |
| MODIFIED | 有，正文是旧版（**不同才正常**） | 有，正文逐字相同 |
| REMOVED | 有 | 无 |
| RENAMED | from 有、to 无 | from 无、to 有 |

- 全部落「已预同步」：改用 `openspec archive --yes --skip-specs <name>`，并在报告里写明「主 spec 已预同步，跳过 spec 更新」。典型成因是有人合并前先跑了 sync-specs。
- 两列混合，或出现两列之外的状态（如 MODIFIED 的标题在主 spec 里找不到）：停止，原样报告差异并问用户怎么处理。`--skip-specs` 是 change 粒度的全有全无，混合态用它会让没同步的那几条永久停在旧正文；它任何时候都会成功、只是静默跳过，不会替你兜底，**不要**用它掩盖不同源。
- 报「主 spec 现有 scenario 未出现在 modified 块里」：openspec 在防丢 scenario，按提示刷新 delta，不绕过。

`--skip-specs` 只用于第一种情形。这是本文档授权的动作，不属于 `SKILL.md` 说的「自行扩大授权范围」——那条约束的对象是 taskctl 的 gate flag，不是 openspec CLI 参数。

### 失败与续跑

一个 change 卡住不等于整批停摆：已归档的保持已归档，其余 pending 继续逐个处理，最后把处置不了的连同差异一起报告，并问用户是先修再来还是先把能归的归完。CLI 按 `YYYY-MM-DD-<change>` 整名识别已归档 change，重跑本节不重复也不丢。只要还有 change active，第 3 步就会以 `openspec_not_archived` 失败，这是预期的。

若 task 有 `design/` 且设计需要正式落地，此时按 README 记录的落点晋升到已列为 `必须` 的目标仓；不要往 `建议` / `排除` 仓猜落点。

## 3. 落盘

所有 change 都已归档后跑 `archive <id>`（第 1 步确认过就带 `--confirmed`）。落盘会按当下状态重算 gate，而 `--confirmed` 放行的是**重算后的全部 gate**——包括第 1 步没出现、第 2 步之后才冒出来的项。所以带 `--confirmed` 之前先看一眼交付仓有没有多出预期外的改动；拿不准就先跑一次 `--dry-run --confirmed` 看 `confirmations` 里是不是还是那几条。CLI 会：

- 再校验一遍 gate，change 仍 active 就以 `openspec_not_archived` 硬失败；
- 写 `changes.md`（交付仓库与分支、change 状态、门禁覆盖）；
- 把 status 改为 `archived`，移动目录到 `tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`，重建 `INDEX.md`。

最后向用户汇报归档路径、各 change 状态、交付分支，以及 `changes.md` 门禁覆盖里实际放行的每一条——这是 `--confirmed` 唯一的事后对账口，不能省。

归档后还要继续做，用 `restore <id>` 恢复为 active，不要手动移目录。
