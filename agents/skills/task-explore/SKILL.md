---
id: task-explore
name: task-explore
description: 针对任务不明确、周期可能很长或需要复杂问题排查的工作，在当前目录维护 tasks/INDEX.md、tasks/ongoing 与 tasks/archive，按 new / explore / chat / resume / design / decide / save / handoff / archive / reopen / split 阶段推进；split 把当前任务的一个方向拆成子任务。explore 委托 grilling；decide 冻结方案；handoff 把探索任务交给 taskflow 的 {task}-driver，任务转入 handed-off（不归档、留在 ongoing 可见，后续可点名 archive 关闭）。处在 goal 里时，向用户确认的决定改走 task-wizard 审阅，不列选项。在用户点名 task-explore、任务目标不清、长周期探索、复杂排查，或要求恢复/交接/归档/重新打开任务时使用。已有探索任务要交付时用 handoff，不要绕开另起无关 driver。
---

# 任务探索

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

在任务不明确、周期可能会非常长、或进行复杂问题排查时，不断进行探索、询问、排查等操作。不写实现代码。

**探索任务** = `tasks/ongoing|archive/.../{task-name}/`。**taskflow 任务** = `{task-name}-driver`。两套账；唯一桥是 `handoff`。交付进度只认 taskflow checkbox。

**子任务** = 探索期从父任务拆出的完整探索任务，承接一个可独立推进的方向：目录嵌套为 `ongoing/{parent}/{sub}/`，`TASK.md` 带 `parent:`，生命周期（explore / decide / handoff 等）与顶层任务相同。**父任务** = 拥有 ≥1 个子任务的探索任务；纯伞，只聚合与登记，`status` 恒 `ongoing`，**禁止 `handoff`、不建 driver**，`decide` 仅限范围/非目标/拆分原则。**handed-off** = 已交接 taskflow 的状态：任务留在 `ongoing/`，INDEX 可见、可 `resume`，不是归档。子任务与交付期的 taskflow 子 change 互不隶属。

## Goal 里的确认

处在 goal 里（消息里有 `/goal`，或当前有进行中的 goal，或本任务由 Goal 方案交接且方案里带完成判据）时，下文和 `references/` 里每一处要向用户确认、选择或询问的决定，都改为走 task-wizard 的「审阅」。不列选项，不用向用户提问的选择界面。

推荐默认是该处已经写出的默认建议。没有写出默认时，取能让完成判据成立、且不覆盖已有目录、不泄密、不做未点名危险操作的那一条，只审这一条。

派审贴上完成判据、「不做的事」、这条推荐默认，以及在审什么：采纳它能否让完成判据成立。完成程度为高且没有未消失的 P0 或 P1：视为已确认，采纳推荐默认，同一轮继续。冻结未决并交接时，审阅收敛即「按推荐冻结并交接」：本轮 `decide` 完立刻 `handoff`。有 P0 或 P1：写入后再审，不向用户要答复。审阅不通过、派不出或没有结论：停，不列选项。task-wizard 读不到：停并给出安装选项，不改回问用户。

不在 goal 里时，下面的确认规则不变。目标已存在则仍禁止覆盖，不交给审阅放行。

## 阶段

| 阶段 | 何时 | 写入 |
|------|------|------|
| `new` | 立项；从输入推断任务名 | `tasks/ongoing/{task-name}/` + `INDEX.md` |
| `explore` | 不断探索预期目标 | 术语/ADR 可落任务目录；`TASK.md` 须经确认或 `save` |
| `chat` | **默认阶段**：对任务问答 | 默认不写盘 |
| `resume` | 恢复进行中的探索任务 | 任务文档只读；INDEX 漂移可重建 |
| `design` | 针对任务方案设计 | `{taskRoot}/design/` |
| `plan-review` | **可选**：decide 前请名册里的 agent 评审方案 | `{taskRoot}/design/`（评审意见） |
| `decide` | 冻结采纳方案 | `TASK.md` 决策；INDEX |
| `save` | 保存任务最新进展到任务文档 | 更新 `TASK.md` 与 `INDEX.md` |
| `handoff` | 交接给 taskflow，转入 `handed-off` | driver + 任务状态更新 |
| `archive` | 归档确认关闭的探索任务（含 `handed-off` 后收尾） | `tasks/archive/{yyyy-mm-dd}/{task-name}` |
| `reopen` | 把归档探索任务搬回 ongoing | `ongoing/` + `INDEX.md` |
| `split` | 把当前任务的一个方向拆成子任务 | `ongoing/{parent}/{sub}/` + 父 TASK.md 登记表 + `INDEX.md` |

用户点名 `{{slash:task-explore}}` 且首词命中上表阶段名时走该阶段；否则走 `chat`。用户要看任务列表或检索任务时，打印 `INDEX.md`（先 Ongoing，需要时再 Archived），不另造阶段。

## 加载

进入阶段时 **只读该阶段详情**，不要预加载其它 phase 或文档骨架。

| 阶段 | 进入时读取 |
|------|------------|
| `explore` | [references/phase-explore.md](references/phase-explore.md) |
| `design` | [references/phase-design.md](references/phase-design.md)；落盘时再读 [references/design-template.md](references/design-template.md) |
| `plan-review` | [references/phase-plan-review.md](references/phase-plan-review.md) |
| `decide` | [references/phase-decide.md](references/phase-decide.md) |
| `handoff` | [references/phase-handoff.md](references/phase-handoff.md)；委托时再读 `taskflow` |
| `archive` | [references/phase-archive.md](references/phase-archive.md) |
| `reopen` | [references/phase-reopen.md](references/phase-reopen.md) |
| `new` / `save` | 本文件步骤；写文件时再读 [references/task-template.md](references/task-template.md)、[references/index-template.md](references/index-template.md) |
| `split` | 本文件步骤；写文件时再读 [references/task-template.md](references/task-template.md)、[references/index-template.md](references/index-template.md) |
| `chat` / `resume` | 本文件已够 |

写台账（`INDEX.md` / `TASK.md`）时，除该阶段详情外再读 [references/ledger-write-discipline.md](references/ledger-write-discipline.md)；不写台账的阶段不读。

## 布局

默认 `TASKS_ROOT` = 当前工作目录下的 `tasks/`。

```text
tasks/
├── INDEX.md             # 派生索引：快速检索/查看
├── ongoing/{task-name}/
│   ├── TASK.md          # 主文档：目标、进展、未决、决策、交接
│   ├── SUMMARY.md       # 归档时生成的人读时间线总结
│   ├── glossary.md      # 任务内术语（惰性）
│   ├── design/          # 方案、ADR
│   └── {sub}/           # 子任务：含 TASK.md 的子目录（split 创建，只一层）
└── archive/{yyyy-mm-dd}/{task-name}/
```

- `{task-name}`：kebab-case，由输入推断，不追问；描述为空才问「要探索什么？」
- 子任务目录 = 含 `TASK.md` 的子目录（`design/`、`glossary.md` 不算）；只一层，子任务不得再有子任务。
- `{sub}` 全局唯一（跨所有父任务），`split` 时扫全树校验；driver 名规则不变（`{sub}-driver`）。
- 没有 `tasks/` 目录时 **必须先获得确认再创建**。已有 `tasks/` 则可直接建 `ongoing/`、任务目录与缺失的 `INDEX.md`。
- 单任务产物只写当前任务目录。`tasks/INDEX.md` 是唯一允许的根级任务文件；评审、委派回收等产物只写绑定的 `{taskRoot}`（如 `design/review-<slug>.md`），禁止在 `tasks/` 根级创建任务目录之外的新目录（如 `tasks/reviews/`）。禁止写到仓库 `docs/design/`、`docs/adr/`、根 `CONTEXT.md`。
- 是否把 `tasks/` 纳入 git 由项目决定，不要擅自改 `.gitignore`。

## 索引

`tasks/INDEX.md` 供快速检索与查看，**不是第二份真相**。

- 单任务真相只在 `{taskRoot}/TASK.md`
- 列出、选择、搜索任务时 **先读 INDEX.md**
- `new` / `split` / `save` / `decide` / `handoff` / `archive` / `reopen` 必须同步对应行：任务名、标题、日期、一句话目标、相对 `tasks/` 的路径；写入纪律见 [references/ledger-write-discipline.md](references/ledger-write-discipline.md)
- 不要把进展日志或对话抄进索引
- 子任务行的任务列写 `{parent}/{sub}`、路径列写嵌套路径；父归档整树搬家后把子行路径批量更新为新位置
- 发现漂移（目录有、索引无，或索引指向不存在的路径）：按 `ongoing/` 与 `archive/` 下的 `TASK.md`（含 `ongoing/{parent}/{sub}/` 一层子目录）**重建** INDEX，再继续
- 已有 `tasks/` 但没有 INDEX：在需要列表或下一次会写 INDEX 的阶段重建，不必再问
- `handed-off` 行（含子任务）的一句话以 `→ {task-name}-driver` 结尾；父任务行一句话聚合子任务状态（如「3 子任务：2 已交接、1 设计中」）

## 绑定（强制）

会话绑定 `{task-name}` + `{taskRoot}` = `tasks/ongoing/{task-name}`（`reopen` 完成前 `{taskRoot}` 仍在 archive）。绑定子任务时任务名显示为 `{parent}/{sub}`，`{taskRoot}` = `tasks/ongoing/{parent}/{sub}/`。

**无 task 上下文时，应提示创建或者恢复（给出 ongoing 列表选择），在确认后进行 new/resume 阶段。** 归档要拉回则走 `reopen`。不得猜测任务、不得先聊后补目录。

1. 先读 `tasks/INDEX.md` 的 Ongoing 表；无 INDEX 或发现漂移则扫 `ongoing/` 并重建。列出任务名 + 标题/一句话。无 `tasks/` 或 Ongoing 为空则说明「当前没有进行中的任务」。
2. 请用户选择：**创建**（`new`）或 **恢复**（`resume`，从列表选）。
3. 用户确认前不进入 `chat` / `explore` / `design` / `decide` / `save` / `handoff` / `archive`。

例外：用户本轮已明确 `new`/`resume`/`reopen`/`handoff` 及对象。`ongoing/` 仅一项且用户说「继续/恢复」→ 可直接 `resume` 该项。

同名 `ongoing/{task-name}` 已存在时，禁止覆盖；改为提议 `resume` 或换名。

## 进展提示

**在任务有进展时提示是否更新任务文档。** 适用于 `explore` / `chat` / `design` / `decide` 之后出现了新目标、新发现、新决策或新缺口。

- 提示一次即可，不阻断继续问答。
- 用户同意 → 按 `save` 写回（含 INDEX）。
- 用户点名 `save` → 直接写，不必再问。

---

## `new`

1. 若没有 `tasks/`：**询问是否在当前位置创建 `tasks/`**。未确认则停止。
2. 推断 `{task-name}`。冲突则列出已有任务并问 resume 还是换名。在已有任务下拆子方向不属于 `new`，走 `split`。
3. 创建 `tasks/ongoing/{task-name}/TASK.md`（用模板，填已知目标）。输入含现成方案（含上游 task-wizard 的步骤级方案）时，把完成判据、事实、假设、步骤、阻塞点、坑一并登记进「方案」小节，不丢上游产物。输入里没有完成判据时不要编造。
4. 在 `tasks/INDEX.md` 的 Ongoing 表追加一行（无 INDEX 则按模板创建或按目录重建）。
5. 绑定该任务。报告路径，询问下一步：`explore`（默认建议）还是 `chat`。不要自动开始 grill。

## `explore`

不断探索预期目标，委托 `grilling`。进入本阶段后 **先读** [references/phase-explore.md](references/phase-explore.md)，再开始提问。未读完不要 grill。禁止调用 `grill-with-docs` / `domain-modeling`。会改方案走向的未知，按该阶段详情做完外部参照再问。

## `chat`（默认）

对任务进行问答：解释、排查、对照代码与已有笔记。先读任务文档再答。

- 只读本仓代码与任务里已有笔记，不做外部参照；不要开始实现。
- 不要把 `chat` 默认为 `explore`（不自动 grill）或 `design`（不写方案稿）。
- 用户要把方案写下来 → 转 `design`。目标仍糊 → 建议 `explore`。路径已清、要交付 → `decide` 然后 `handoff`，不要直接开一个无关名字的 driver。
- 发现任务含多个可独立推进的方向 → 提示一次可 `split` 拆子任务，不阻断，用户确认才建。
- 用户要看有哪些任务 → 打印 INDEX，不进入 `new`。
- 有进展则提示是否更新任务文档。

## `resume`

恢复进行中的探索任务。**任务文档只读**；发现 INDEX 漂移时允许重建 `INDEX.md`，不要改 `TASK.md` / `glossary.md` / `design/`。

1. 未指定名字：用 INDEX 的 Ongoing 表列出请用户选。指定了则用该名字。
2. 任务不在 `ongoing/`：先查 INDEX 的 Archived 表，再扫 `tasks/archive/`。告知已归档路径；**不要自动恢复**，拉回走 `reopen`。找不到则说明，改走 `new`。
3. 读 `TASK.md`、`glossary.md`、`design/`（有则读索引与最新稿）。恢复子任务时先只读父 `TASK.md` 的目标/决策节防方向漂移，再读子任务全套；父文档不被修改。
4. 用短摘要恢复：**目标 / 当前进展 / 未决 / 建议下一步**（`explore` / `chat` / `design` / `decide` / `save` / `handoff` / `archive`）。然后等用户。

## `design`

方案写入 `{taskRoot}/design/`，不写 `docs/design/`。**方案不明朗时主动打断，提示缺口。** 进入本阶段后 **先读** [references/phase-design.md](references/phase-design.md)；落盘时再读 [references/design-template.md](references/design-template.md)。写对比表之前按阶段详情做一次外部参照。方案成形后可走 `plan-review` 找名册里的 agent 评审，再 `decide`。

## `plan-review`（可选）

在 `design` 与 `decide` 之间：把成形方案交给名册里的 agent 评审，回收意见后回 `design` 修正。**可选**——用户不要求则跳过，直接 `decide`；用户/同事已评审也算完成。

评审是**只读**委派，直接委托 `$agent-roster`（单次评审，不走 `$agent-roster-flow`）。进入本阶段后 **先读** [references/phase-plan-review.md](references/phase-plan-review.md)。

候选收成编号表（Endpoint / Model / 擅长方向 / 依据）供用户圈选；名册里没有合适候选时直接问用户，**不要凭 CLI 名假设可用**。名册查询、`decision.md`、acpx 门禁、失败分类与留痕一律按 `$agent-roster`，本阶段不复制其契约。

## `decide`

冻结采纳方案。进入本阶段后 **先读** [references/phase-decide.md](references/phase-decide.md)。没有可冻结的方案就打断。方案未经 `plan-review` 不阻断；想先评审则走 `plan-review`。用户说「按推荐冻结并交接」时，本轮 `decide` 完立刻 `handoff`。处在 goal 里时不逐条问用户，按「Goal 里的确认」走审阅；审阅收敛则同样本轮 `decide` 完立刻 `handoff`。

同一任务可多次 `decide`：新决策追加编号写入决策小节，被取代的旧决策标注「被 D-n 取代」而非删除。带默认值的未决问题须逐条经用户确认后才算冻结；处在 goal 里时这一确认改为审阅。未确认项保持开放。父任务的 `decide` 仅限范围、非目标与拆分原则，具体方案属各子任务。

## `save`

保存任务最新进展到任务文档。

1. 必须已绑定。读现有 `TASK.md`，合并本轮进展，不抹掉仍有效的旧内容。
2. 更新 `updated`、目标/非目标、现状、进展、决策、交接、未决、下一步。有设计结论则链到 `design/`。
3. 同步更新 `INDEX.md` 中该任务的标题、日期、一句话目标；不要把进展日志抄进索引。
4. 不要贴聊天记录。无新进展则说明无需写入。
5. 报告改了哪些文件。

## `handoff`

把探索任务交给 taskflow（`{task-name}-driver`），任务转入 `handed-off`；**不归档、不搬目录、不清绑定**。进入本阶段后 **先读** [references/phase-handoff.md](references/phase-handoff.md)。交接目标按绑定自动推断，无需用户逐项指定：

- 绑定子任务 → 交接该子任务，建 `{sub}-driver`。
- 绑定父任务 → 父是纯伞不可交接，自动批量交接所有「已 `decide` 未交接」的子任务，无需逐项确认；就绪为零则打断并报告各子任务所缺条件；未 `decide` 的子任务跳过且不阻塞其余。批量中任一失败即停，已交接的不回滚。
- 父任务无子任务 → 提示 `split` 拆分或 `new` 另建，**不建 `{parent}-driver`**。

**`handed-off` 状态**：任务留在 `tasks/ongoing/`，INDEX 的 Ongoing 表保留该行（一句话以 `→ {task-name}-driver` 结尾）；可 `resume` 查看方案/决策/交接记录，交付进度只认 taskflow checkbox，任务文档不再勾交付进度；再次 `handoff` 只报告 driver 路径。方案修订默认直接改 driver 的 `proposal.md`；改动大或要推翻决策时，点名 `reopen` 撤回交接（`status` 回 `ongoing`）后重新 `decide` → `handoff`。

## `archive`

对确认关闭的探索任务归档（不交接而结束、或 `handed-off` 后确认无需回溯），整树搬到 `tasks/archive/{yyyy-mm-dd}/{task-name}`。要交付请用 `handoff`，不要用本阶段代替交接。进入本阶段后 **先读** [references/phase-archive.md](references/phase-archive.md)，未读完不得搬目录。

门禁按序执行、任一不过即停；步骤与细则在 reference，下列五条不可跳过：

- 必须已绑定或用户给出名字，且拿到用户「确认关闭」的明确答复；只给名字不算确认，未确认不搬。
- **目标已存在则停止并询问，禁止覆盖；此时不得改 `TASK.md`、不得移动目录、不得改 INDEX。**
- 存在子任务目录时：所有子任务 `status` 必须为 `handed-off` 或 `archived`，否则打断并列出未结子任务。父任务归档即整树关闭。
- 未决问题、曾 `handed-off` 的 driver 交付进度、指向旧路径的入链，三项必须清点并合并成一次确认后才搬。
- 必须在 `TASK.md` 留下本次结论与关闭原因，并写 `{taskRoot}/SUMMARY.md`（给人读的时间线总结）；曾 `handed-off` 的任务必须先按 `save` 落盘才搬。`archived` 日期在元信息、目录名、INDEX 三处一致。

不要把任务内容晋升到 `docs/design/` 或其它项目文档，除非用户另说。

## `reopen`

把已 `archive` 的探索任务搬回 `tasks/ongoing/{task-name}`；或对 `handed-off` 任务撤回交接（目录不动，只改状态）。进入本阶段后 **先读** [references/phase-reopen.md](references/phase-reopen.md)，未读完不得搬目录。

定位分支与步骤在 reference，下列四条门禁不可跳过：

- 必须拿到用户「确认 reopen」的明确答复；只给任务名不算确认。
- **目标已存在则停止并询问，禁止覆盖；此时不得改 `TASK.md`、不得移动目录、不得改 INDEX。**
- 状态以 `TASK.md` 的 `status` 为准，不按目录位置猜；已 `handed-off` / 已 `archived` 的子任务不自动复活，driver 一律不删。
- 撤回 `handed-off` 后，INDEX 行留在 Ongoing 但去掉 `→ {task-name}-driver` 尾注。

---

## `split`

从当前绑定的探索任务拆出子任务，承接一个可独立推进的方向。子任务是完整探索任务，只是目录嵌套、`TASK.md` 带 `parent:`。

1. 必须已绑定，绑定任务即父任务。绑定任务本身是子任务（`TASK.md` 已有 `parent:`）则停止：子任务只一层，提示改用 `decide` / `handoff` 收敛。
2. 缺 `{sub}` 名或一句话方向则询问；`explore` / `chat` 中发现可拆方向时只提示一次，不自动创建。
3. `{sub}` 用 kebab-case，且 **全局唯一**：扫 `ongoing/` 全树（含各父目录的子目录）无同名，冲突则换名。
4. 创建 `ongoing/{parent}/{sub}/TASK.md`（用模板）：填 `parent: {parent}`，目标节写该方向的子目标，现状节链接父 `TASK.md` 相关段落。
5. 父 `TASK.md` 的 **子任务** 小节登记一行（无该小节则新建）：`{sub}`、一句话方向、状态、创建日期。
6. `INDEX.md` Ongoing 表追加一行：任务列 `{parent}/{sub}`，路径列 `ongoing/{parent}/{sub}/`。
7. 绑定切换到子任务，报告路径，询问下一步（默认建议 `explore`）。父任务随时可 `resume` 回来。父任务 `status` 恒 `ongoing`、自身无独立进度；`handoff` 永不针对父（对父点名 `handoff` = 自动批量交接就绪子任务），父也永不建自己的 driver。

---

## 何时不用

| 情况 | 改用 |
|------|------|
| 从未建探索任务，范围清楚、马上实现 | 直接实现，或 `taskflow` / `openspec-propose` |
| 已有探索任务，路径已清、要交付 | 本 skill 的 `handoff`（不要另起无关 `{task}-driver` 名） |
| 只要读代码、不需要任务台账 | `dotf-code-explore` |
| 只要一次 grill、不需要 `tasks/` | `grill-with-docs` / `grilling` |
| 已在 OpenSpec change 里交付 | `taskflow` + `openspec-*` |
