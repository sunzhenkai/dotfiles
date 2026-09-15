---
id: task-explore
name: task-explore
description: 针对任务不明确、周期可能很长或需要复杂问题排查的工作，在当前目录维护 tasks/INDEX.md、tasks/ongoing 与 tasks/archive，按 new / explore / chat / resume / design / decide / save / handoff / archive / reopen 阶段推进。explore 委托 grilling；decide 冻结方案；handoff 把探索任务交给 taskflow 的 {task}-driver 后归档。在用户点名 task-explore、任务目标不清、长周期探索、复杂排查，或要求恢复/交接/归档/重新打开任务时使用。已有探索任务要交付时用 handoff，不要绕开另起无关 driver。
---

# 任务探索

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

在任务不明确、周期可能会非常长、或进行复杂问题排查时，不断进行探索、询问、排查等操作。不写实现代码。

**探索任务** = `tasks/ongoing|archive/.../{task-name}/`。**taskflow 任务** = `{task-name}-driver`。两套账；唯一桥是 `handoff`。交付进度只认 taskflow checkbox。

## 阶段

| 阶段 | 何时 | 写入 |
|------|------|------|
| `new` | 立项；从输入推断任务名 | `tasks/ongoing/{task-name}/` + `INDEX.md` |
| `explore` | 不断探索预期目标 | 术语/ADR 可落任务目录；`TASK.md` 须经确认或 `save` |
| `chat` | **默认阶段**：对任务问答 | 默认不写盘 |
| `resume` | 恢复进行中的探索任务 | 任务文档只读；INDEX 漂移可重建 |
| `design` | 针对任务方案设计 | `{taskRoot}/design/` |
| `decide` | 冻结采纳方案 | `TASK.md` 决策；INDEX |
| `save` | 保存任务最新进展到任务文档 | 更新 `TASK.md` 与 `INDEX.md` |
| `handoff` | 交接给 taskflow 后归档 | driver + 归档探索任务 |
| `archive` | 归档已结束、不交接的探索任务 | `tasks/archive/{yyyy-mm-dd}/{task-name}` |
| `reopen` | 把归档探索任务搬回 ongoing | `ongoing/` + `INDEX.md` |

用户点名 `{{slash:task-explore}}` 且首词命中上表阶段名时走该阶段；否则走 `chat`。用户要看任务列表或检索任务时，打印 `INDEX.md`（先 Ongoing，需要时再 Archived），不另造阶段。

## 加载

进入阶段时 **只读该阶段详情**，不要预加载其它 phase 或文档骨架。

| 阶段 | 进入时读取 |
|------|------------|
| `explore` | [references/phase-explore.md](references/phase-explore.md) |
| `design` | [references/phase-design.md](references/phase-design.md)；落盘时再读 [references/design-template.md](references/design-template.md) |
| `decide` | [references/phase-decide.md](references/phase-decide.md) |
| `handoff` | [references/phase-handoff.md](references/phase-handoff.md)；委托时再读 `taskflow` |
| `new` / `save` | 本文件步骤；写文件时再读 [references/task-template.md](references/task-template.md)、[references/index-template.md](references/index-template.md) |
| `chat` / `resume` / `archive` / `reopen` | 本文件已够 |

## 布局

默认 `TASKS_ROOT` = 当前工作目录下的 `tasks/`。

```text
tasks/
├── INDEX.md             # 派生索引：快速检索/查看
├── ongoing/{task-name}/
│   ├── TASK.md          # 主文档：目标、进展、未决、决策、交接
│   ├── glossary.md      # 任务内术语（惰性）
│   └── design/          # 方案、ADR
└── archive/{yyyy-mm-dd}/{task-name}/
```

- `{task-name}`：kebab-case，由输入推断，不追问；描述为空才问「要探索什么？」
- 没有 `tasks/` 目录时 **必须先获得确认再创建**。已有 `tasks/` 则可直接建 `ongoing/`、任务目录与缺失的 `INDEX.md`。
- 单任务产物只写当前任务目录。`tasks/INDEX.md` 是唯一允许的根级任务文件。禁止写到仓库 `docs/design/`、`docs/adr/`、根 `CONTEXT.md`。
- 是否把 `tasks/` 纳入 git 由项目决定，不要擅自改 `.gitignore`。

## 索引

`tasks/INDEX.md` 供快速检索与查看，**不是第二份真相**。

- 单任务真相只在 `{taskRoot}/TASK.md`
- 列出、选择、搜索任务时 **先读 INDEX.md**
- `new` / `save` / `decide` / `handoff` / `archive` / `reopen` 必须同步对应行：任务名、标题、日期、一句话目标、相对 `tasks/` 的路径
- 不要把进展日志或对话抄进索引
- 发现漂移（目录有、索引无，或索引指向不存在的路径）：按 `ongoing/` 与 `archive/` 下的 `TASK.md` **重建** INDEX，再继续
- 已有 `tasks/` 但没有 INDEX：在需要列表或下一次会写 INDEX 的阶段重建，不必再问
- `handoff` 归档行的一句话以 `→ {task-name}-driver` 结尾

## 绑定（强制）

会话绑定 `{task-name}` + `{taskRoot}` = `tasks/ongoing/{task-name}`（`reopen` 完成前 `{taskRoot}` 仍在 archive）。

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
- 不要把整段对话粘进 `TASK.md`。

---

## `new`

1. 若没有 `tasks/`：**询问是否在当前位置创建 `tasks/`**。未确认则停止。
2. 推断 `{task-name}`。冲突则列出已有任务并问 resume 还是换名。
3. 创建 `tasks/ongoing/{task-name}/TASK.md`（用模板，填已知目标）。
4. 在 `tasks/INDEX.md` 的 Ongoing 表追加一行（无 INDEX 则按模板创建或按目录重建）。
5. 绑定该任务。报告路径，询问下一步：`explore`（默认建议）还是 `chat`。不要自动开始 grill。

## `explore`

不断探索预期目标，委托 `grilling`。进入本阶段后 **先读** [references/phase-explore.md](references/phase-explore.md)，再开始提问。未读完不要 grill。禁止调用 `grill-with-docs` / `domain-modeling`。

## `chat`（默认）

对任务进行问答：解释、排查、对照代码与已有笔记。先读任务文档再答。

- 可只读查代码与资料；不要开始实现。
- 不要把 `chat` 默认为 `explore`（不自动 grill）或 `design`（不写方案稿）。
- 用户要把方案写下来 → 转 `design`。目标仍糊 → 建议 `explore`。路径已清、要交付 → `decide` 然后 `handoff`，不要直接开一个无关名字的 driver。
- 用户要看有哪些任务 → 打印 INDEX，不进入 `new`。
- 有进展则提示是否更新任务文档。

## `resume`

恢复进行中的探索任务。**任务文档只读**；发现 INDEX 漂移时允许重建 `INDEX.md`，不要改 `TASK.md` / `glossary.md` / `design/`。

1. 未指定名字：用 INDEX 的 Ongoing 表列出请用户选。指定了则用该名字。
2. 任务不在 `ongoing/`：先查 INDEX 的 Archived 表，再扫 `tasks/archive/`。告知已归档路径；**不要自动恢复**，拉回走 `reopen`。找不到则说明，改走 `new`。
3. 读 `TASK.md`、`glossary.md`、`design/`（有则读索引与最新稿）。
4. 用短摘要恢复：**目标 / 当前进展 / 未决 / 建议下一步**（`explore` / `chat` / `design` / `decide` / `save` / `handoff` / `archive`）。然后等用户。

## `design`

方案写入 `{taskRoot}/design/`，不写 `docs/design/`。**方案不明朗时主动打断，提示缺口。** 进入本阶段后 **先读** [references/phase-design.md](references/phase-design.md)；落盘时再读 [references/design-template.md](references/design-template.md)。

## `decide`

冻结采纳方案。进入本阶段后 **先读** [references/phase-decide.md](references/phase-decide.md)。没有可冻结的方案就打断。用户说「按推荐冻结并交接」时，本轮 `decide` 完立刻 `handoff`。

## `save`

保存任务最新进展到任务文档。

1. 必须已绑定。读现有 `TASK.md`，合并本轮进展，不抹掉仍有效的旧内容。
2. 更新 `updated`、目标/非目标、现状、进展、决策、交接、未决、下一步。有设计结论则链到 `design/`。
3. 同步更新 `INDEX.md` 中该任务的标题、日期、一句话目标；不要把进展日志抄进索引。
4. 不要贴聊天记录。无新进展则说明无需写入。
5. 报告改了哪些文件。

## `handoff`

把探索任务交给 taskflow（`{task-name}-driver`），成功后归档。进入本阶段后 **先读** [references/phase-handoff.md](references/phase-handoff.md)。无决策则先 `decide`。driver 未就绪则 **不归档**。

## `archive`

对不交接的探索任务归档，放到 `tasks/archive/{yyyy-mm-dd}/{task-name}`。要交付请用 `handoff`，不要用本阶段代替交接。

1. 必须已绑定或用户给出名字。先确认；未确认不搬。
2. 计算目标路径 `tasks/archive/{yyyy-mm-dd}/{task-name}`。**目标已存在则停止并询问，禁止覆盖；此时不得改 `TASK.md`、不得移动目录、不得改 INDEX。**
3. 建议先 `save` 再搬；用户拒绝则按现状归档。
4. 把 `TASK.md` 的 `status` 改为 `archived`，写入归档日期。
5. `mkdir -p tasks/archive/{yyyy-mm-dd}`，再把整个 `{taskRoot}` **移动**过去。
6. 把 INDEX 中该行从 Ongoing 移到 Archived（归档日与新路径）；无 INDEX 则重建。
7. 清除会话绑定。报告新路径。

不要把任务内容晋升到 `docs/design/` 或其它项目文档，除非用户另说。

## `reopen`

把归档中的探索任务搬回 `tasks/ongoing/{task-name}`。

1. 未指定名字：用 INDEX 的 Archived 表列出请用户选。指定了则用该名字。
2. 在 `tasks/archive/` 定位目录。找不到则停止。
3. 计算目标 `tasks/ongoing/{task-name}`。**目标已存在则停止并询问；此时不得改 `TASK.md`、不得移动目录。**
4. 先确认；未确认不搬。
5. 把 `TASK.md` 的 `status` 改回 `ongoing`，保留已有决策/交接记录。若曾 `handoff`，警告 `{task-name}-driver` 可能仍在，不要删 driver。
6. 移动目录到 `ongoing/`。把 INDEX 该行从 Archived 移回 Ongoing。绑定该探索任务。
7. 用短摘要恢复上下文，等用户选下一步。

---

## 何时不用

| 情况 | 改用 |
|------|------|
| 从未建探索任务，范围清楚、马上实现 | 直接实现，或 `taskflow` / `openspec-propose` |
| 已有探索任务，路径已清、要交付 | 本 skill 的 `handoff`（不要另起无关 `{task}-driver` 名） |
| 只要读代码、不需要任务台账 | `dotf-code-explore` |
| 只要一次 grill、不需要 `tasks/` | `grill-with-docs` / `grilling` |
| 已在 OpenSpec change 里交付 | `taskflow` + `openspec-*` |

## 相关

进入对应阶段再读，不要一次性打开：

- [references/phase-explore.md](references/phase-explore.md) — `explore`
- [references/phase-design.md](references/phase-design.md) — `design`
- [references/phase-decide.md](references/phase-decide.md) — `decide`
- [references/phase-handoff.md](references/phase-handoff.md) — `handoff`
- [references/design-template.md](references/design-template.md) — design 落盘
- [references/task-template.md](references/task-template.md) — `new` / `save` / `decide`
- [references/index-template.md](references/index-template.md) — 建或重建 INDEX
- `grilling` — `explore` 委托
- `taskflow` — `handoff` 委托的交付生命周期
- `dotf-code-explore` — 只读代码理解
