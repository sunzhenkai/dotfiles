---
id: task-workflow
name: task-workflow
description: 跟踪一次需求交付（new/explore/design?/propose/apply/archive）；task-* 家族入口。工作区根 `.task-workflow.md` 保存跨任务特殊要求与规格。在用户要立项、跟进需求任务、把 OpenSpec change 与交付生命周期串起来时使用。复杂任务可在 explore 之后走可选的 task-design。
---

# 任务工作流

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

`task-*` 命令的共享执行细节（SSOT）。各 `{{slash:task-new}}` 等 command 仅为薄壳，**MUST** 先读本 skill 再执行对应「各命令职责」小节。

推荐链路：

```
task-new → task-explore? → task-design? → task-propose → task-apply → task-archive
```

`task-design` 为**可选**环节：新子系统、多方案权衡、跨模块契约时用；范围局部且路径唯一则可跳过，explore 后直接 propose。设计方法见 skill `task-design`；本 skill 管 Resolution / Checkout Gate、`design/` 落盘与归档晋升。

`tasks/` 与 `openspec/changes/` 为并行容器：tasks 跟踪交付生命周期，OpenSpec 承载可验证契约；互不替代。task 侧通过委托 `openspec-explore` / `openspec-propose` / `openspec-apply-change` / `openspec-archive-change`（若已安装对应 skill；否则用 `openspec` CLI 与仓库 `openspec/` 约定完成同等步骤）完成契约工作。

## taskctl（优先）

机械步骤 **MUST** 走 CLI，避免手改 `tasks/INDEX.md` 表格或多轮猜测解析。脚本与本 `SKILL.md` 同级，位于 `scripts/taskctl.py`：

```bash
python3 <this-skill>/scripts/taskctl.py <cmd> ...
```

`<this-skill>` 是包含本 `SKILL.md` 的目录（安装后常见于 `~/.cursor/skills/task-workflow/` 或项目 `.cursor/skills/task-workflow/`）。**不要**假设脚本在当前仓库根下。

| 子命令 | 用途 | 退出码 |
|--------|------|--------|
| `list` | 列出活跃任务（JSON） | 0 |
| `resolve [query] --command <cmd> [--hint ...] [--cwd ...] [--git-branch ...]` | Task Resolution Gate；无 query 时自动推断 | 0 确定性唯一；**2** 零/多命中/需确认 |
| `set-status <query> <status>` | 同步写 README status + INDEX 行 | 0 / 2 |
| `new [--slug <slug>] [--title ...] [--date YYYY-MM-DD]` | 分配 `TNNNN`、建目录与 README 骨架、更新 INDEX。`--slug` / `--title` 至少其一；无 slug 时从 title 推导 | 0 |
| `archive <query> [--allow-missing-changes] [--force-merge]` | status→archived、移至 `tasks/archive/`、更新 INDEX | 0 / 2 |
| `repo-roots <path> [...]` | 解析为去重后的 git 根（工作区相对路径；`.` = 工作区自身，仅当工作区就是目标仓时使用） | 0 / 1 |
| `scope-repos <query> [--cwd ...]` | 解析 README 涉及面；`checkout` 仅为角色=必须的仓 | 0 / 2 |
| `prepare-branches --slug <slug> [--from-task <query>] [--repo <path>] [--worktree REPO=CHECKOUT]` | Checkout Gate：解析/创建/续用真实 checkout，刷新基线并自动记账 | 0 / 1 / 2 |
| `execution-context <query>` | 解析 task 的真实 checkout、OpenSpec planning root 与现有进度 | 0 / 2 |
| `checkpoint <query> --phase ...` | 强制保存 apply 阶段、当前项、阻塞、验证证据、下一步与 Git 快照 | 0 / 2 |
| `git-summary --repo <path> [--checkout REPO=CHECKOUT] [--branch ...] [--base ...]` | 只读提交及工作树 diff，产出 `changes.md` 素材 | 0 / 1 |
| `notes` | 读写工作区根 `.task-workflow.md`（`--init` / `--from-file` / `--set-section`） | 0 / 1 |

- stdout：**仅 JSON**（`ok` / `result` / `task` 或 `exit_markdown`）。
- stderr：一行人读摘要（如「当前任务：T0002 — path」）。
- `resolve`/`set-status`/`archive` 在零/多命中或 `needs_confirm` 时打印 `exit_markdown`，**中止主流程**，等待用户选择。
- `new` 只建骨架；概述/现状缺口/涉及面/工作上下文/验收等正文仍由 Agent 填写。`--slug` 可省略：有 `--title` 且含足够 ASCII 词时 CLI 会推导 slug；中文为主的标题由 Agent 按语义自推 kebab-case，**不要为此问用户**。
- `archive` 默认要求已有 `changes.md`（OpenSpec 归档与正文结论先做完）。只剩测试/验证 checkbox 时 **MUST** `needs_confirm`（退出码 2），列出剩余项并等用户选择；禁止自行当结案停止，也禁止未确认就归档。用户确认「继续归档 / 强行合并」或本条已写该口令后，用 `--force-merge` 覆盖未完成 OpenSpec（原因写入 `changes.md`）。仍有实现项则硬失败，除非用户明确强行合并。
- `prepare-branches`：身份确定后、**写入目标代码仓之前**跑。优先级为显式 `--worktree` → README 已记录 checkout → 已持有 task 分支的 worktree → canonical 仓。显式 checkout 不存在时创建 linked worktree；工作区外路径仅在 `git-common-dir` 同源时可续用。配置了 `origin` 但 fetch 失败必须阻断，禁止从旧本地基线继续。`--from-task` 会自动回写工作上下文；部分仓成功后也保存成功项。无必须仓则跳过。已在目标分支允许 dirty 续作；其他 dirty 情况停下来确认。支持 `--dry-run`；不 push；禁止擅自 stash/reset/force checkout。
- `execution-context`：`task-apply` / archive 写操作前 MUST 调用；不得依赖当前 cwd 猜 OpenSpec 根。JSON 含 `openspec_remaining.kind`（`none` / `verification_only` / `implementation`）与剩余 checkbox 文本，供 archive 门禁判断。
- `checkpoint`：`task-apply` 开始、每个 OpenSpec task 完成、暂停/错误、进入测试和全部完成时 MUST 调用；`progress.md` 不再可选。
- `scope-repos`：只读解析涉及面。`checkout` = 必须仓路径；建议/排除不在内。cwd 出现在 `cwd_*` 报告里，不自动进入 checkout。
- `git-summary`：只读；路径以仓库相对前缀输出；禁止为采摘要而改工作区；`--repo` 同样只传必须仓。
- `notes`：读/建/改工作区根 `.task-workflow.md`。`--init` 仅在文件不存在时建骨架；`--set-section` 在缺失时先建骨架再写入一节；`--from-file` 整文件替换。`resolve` / `new` JSON 亦含 `workflow_notes`。
- 可选 `--root <工作区根>`；默认从 cwd 向上探测含 `tasks/` 的目录。

## 任务编号与索引

SSOT：`tasks/INDEX.md`（由 `taskctl` 维护；勿手搓表格除非 CLI 不可用）。

### 编号

- 格式：`T` + 四位数字，如 `T0001`（大小写不敏感，规范化为大写 `T` + 零填充）
- 分配：`taskctl new` 读取 INDEX frontmatter `next_id`，分配后 `next_id += 1`
- 快捷指定：后续命令可用 `T0001` 唯一命中任务（优先于 slug）

### 目录

- 活跃：`tasks/YYYY-MM-DD/TNNNN-<slug>/`
- 归档：`tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`（日期取自原活跃目录的创建日）
- `<slug>`：kebab-case，全小写，仅字母、数字、连字符
- 遗留无编号目录（仅 `<slug>`）仍可通过 INDEX 登记的 ID 或 slug 解析；**新任务 MUST 使用带编号目录名**

### INDEX.md

frontmatter：

```yaml
---
next_id: 3
---
```

正文维护两张表（活跃 / 已归档）。
每次 `{{slash:task-new}}`、status 变更、`{{slash:task-archive}}` MUST 经 `taskctl` 更新 INDEX。

## Task Resolution Gate

除 `{{slash:task-new}}` 外，所有 task command **第一步 MUST** 调用 `resolve`。

`taskctl` **看不到会话历史**，只看传入的 query 与 `--hint`。Agent **MUST** 先从本条消息和本会话上文抽出明确任务，再决定怎么调 `resolve`。

**组 query / --hint（Agent MUST）**

1. 本条已有唯一 `TNNNN` / `TNNNN-<slug>` / `tasks/...` 路径 → **显式 query**，不要 `--infer`
2. 本条没有，但本会话上文已有**明确焦点任务** → **同样显式 query**。典型信号（须能指到唯一活跃 task，满足其一即可）：
   - 本会话刚对该编号跑过 `task-apply` / `task-propose` / `task-design` / `task-explore`
   - 桥接块已写带编号命令（如 `/task-archive T0007`）
   - 用户刚对该任务打 tag / push，或说「归档当前任务」且上文编号唯一
   - 上一条用户或助手已点名唯一 `TNNNN`
3. 上文出现多个不同 `TNNNN` 且无法判断焦点 → `--infer`，**把这些编号都放进 `--hint`**；`needs_confirm` 时再问
4. `--hint` MUST 包含：用户本条原文 + 本会话已点名的 `TNNNN`（若有）。**禁止**只传命令名（如 `/task-archive`）丢掉上文编号，再拿多个 `in_progress` 去问用户

```bash
# 显式（本条或上文已有唯一编号时 MUST 走这条）
python3 <this-skill>/scripts/taskctl.py resolve <TNNNN|slug|path> --command <当前命令名>

# 未指定且上文也无唯一焦点：自动推断
python3 <this-skill>/scripts/taskctl.py resolve --infer --command <当前命令名> \
  --hint "<用户消息原文> <本会话已点名的 TNNNN，若有>" [--cwd "$PWD"] [--git-branch "<当前分支>"]
```

- 退出码 **0**（`result=unique`，`confidence=deterministic`）：继续主流程。
- 退出码 **2**：输出 `exit_markdown` 并**中止**；`needs_confirm` 时列出候选，**等用户选择编号**后再继续。不得写 task 文档、委托 OpenSpec 写操作、建分支或移动目录。

### 解析 / 推断优先级（由 taskctl 实现）

**显式 query（确定性）**

1. 任务编号 `T0001`
2. `TNNNN-<slug>` / `<slug>` / `tasks/<date>/.../`

**无 query 时自动推断**

| 优先级 | 来源 | 置信度 | 行为 |
|--------|------|--------|------|
| 1 | 仅 1 个活跃 task（`sole_active`） | deterministic | 直接采用 |
| 2 | `--hint` 中的 `TNNNN` / `tasks/...` 路径（唯一） | deterministic | 直接采用 |
| 3 | `--cwd` 落在某活跃 task 目录下 | deterministic | 直接采用 |
| 4 | `--git-branch` 形如 `feat-<slug>` 且唯一命中 | deterministic | 直接采用 |
| 5 | 按命令偏好 status（如 apply→`in_progress`/`proposed`） | heuristic | **needs_confirm** |
| 6 | 最新创建日 / 更新日排序 | heuristic | **needs_confirm** |

- heuristic（非确定性）无论候选 1 个还是多个，都 **MUST** 让用户确认/选择。
- **禁止**未跑 `resolve` 就选定 task；**禁止**把 OpenSpec change 名当成 task id。
- **允许且必须**：把本会话已点名的唯一 `TNNNN` 当作显式 query（这不是「模糊印象」）。

## README status

| status | 含义 | 写入方 |
|--------|------|--------|
| `draft` | 已创建 | task-new / `taskctl new` |
| `exploring` | 方案探索中 | task-explore → `taskctl set-status` |
| `designed` | 已有 task 内设计文档 | task-design → `taskctl set-status` |
| `proposed` | 已有关联 OpenSpec change | task-propose → `taskctl set-status` |
| `in_progress` | 实施中 | task-apply → `taskctl set-status` |
| `blocked` | 有阻塞项 | task-apply → `taskctl set-status` |
| `archived` | 已归档 | task-archive → `taskctl archive` |

缺 status 时 Gate 视为 `draft`。状态以 README 为准；INDEX 经 `set-status`/`archive` 对齐。

## README 必填

- 文首元信息：`id`（TNNNN）、`status`、`slug`、创建时间（`taskctl new` 骨架已含）
- 概述、背景、目标、**现状缺口**、需求说明、验收标准（checkbox）、变更记录
- **现状缺口**（task-new 必填）：对照目标列出需补充的内容；类型用 `信息 / 实现 / 资产 / 配置 / 依赖确认`；每条附建议补齐方式（追问 / `{{slash:task-explore}}` / 调研等）。未知标「待确认」；确无缺口写「暂无（目标范围内现状已齐）」。后续 explore/propose 可修订。
- **涉及面**：本任务会**修改**的目标仓库相对路径 / 是否跨仓（task-new 梳理；后续可修正）。角色=必须 才会被 Checkout Gate 切分支。只读参考仓不要写进必须。
- **工作上下文**：实际执行环境（是否 git worktree、实际写入的代码库与分支）。事实一出现或变化就立刻改，不要等 archive。详见下节。
- **关联 OpenSpec**：change 名与路径列表（task-propose 写入；可多个；`taskctl resolve` 会解析该表）
- **设计文档**（task-design 写入）：`design/` 下文件与归档落点表；未做设计则保持「尚无」
- 不得含明文密钥或数据库凭证；需要时写环境变量名 `$VAR_NAME`

## 工作上下文（及时落盘）

每个 task README **MUST** 有「工作上下文」节，记录**实际执行环境**（与「涉及面」的计划范围分开）。事实一出现或变化就立刻改 README，**禁止**只记在对话里或攒到 archive。跨会话续作以本节为准。缺节时，下一个 `task-*` 命令补上，不要因此失败。

**必记（有则写，无则写「未使用 / 无」）：**

| 项 | 记什么 |
|----|--------|
| git worktree | 是否使用；canonical 仓路径 + 实际 checkout 路径 |
| 改动代码库 | 本任务实际写入的 git 仓；**多个必须逐行**，不要只写「多个」 |
| 分支 | 各仓当前 task 分支（`prefix-slug`）与基线（若覆盖默认分支） |

也可记：隔离目录、用户指定的 checkout 路径、与涉及面必须仓不一致之处。禁止写入密钥。

**何时写：** 由 `prepare-branches --from-task` 自动更新；task-new 时根据返回结果补写。用户改用 worktree、增删必须仓、换写入路径时重新运行 Gate。无必须仓写「无必须仓（仅工作区 `tasks/` 记账）」。表列：仓库 / 仓库路径 / checkout 路径 / worktree / 分支 / 基线。

## 路径与仓库

- 工作区：含 `tasks/` 的目录（`taskctl --root` 的探测目标）
- 目标 git 仓：工作区相对路径，且必须是本任务会写入的代码仓。由涉及面「必须」列出，不能仅凭所在目录推断
- `.` 的含义：工作区 git 根本身。仅当工作区就是要改的那个仓时才用 `--repo .`（典型单仓项目）。多仓工作区且工作区自身不是目标仓时，**禁止**传 `.`
- git 操作：从给定路径向上定位含 `.git` 的仓库根；不得逃出工作区；不得顺带切父仓或兄弟仓

**涉及面识别优先级（task-new / design / propose / apply）：**

1. 用户消息明确指定的、**需要修改**的代码库
2. README「涉及面」中角色=必须的路径
3. 关联 OpenSpec change `tasks.md` 中将要写入的仓库路径 → 向上定位 git 根

同一仓库根去重；标注必须 / 建议 / 排除。

- **必须**：本任务会改这个仓（Checkout Gate 只切这些）
- **建议**：相关但本阶段不改（可读，不切分支）
- **排除**：明确无关（不切、不写）

涉及面全量节点 ≠ 本阶段全部建分支。写 `tasks/` 记账**不构成**切换工作区仓的理由。

## 工作区笔记（`.task-workflow.md`）

工作区根（含 `tasks/` 的目录）的 `.task-workflow.md` 记录**跨任务仍有效**的特殊要求、规格说明与默认涉及面。单次任务的概述/验收仍写 task README，不要把一次性需求塞进此文件。

### 何时读写

1. **每个 task-* 命令开始时**：`taskctl notes`（`resolve` / `new` JSON 的 `workflow_notes` 亦可）。`exists=true` 则把其中特殊要求 / 规格说明当作硬约束。
2. **用户给出跨任务约定**（默认仓、分支前缀、保密、OpenSpec 落点、验收习惯等）或发现本工作区稳定规格 / 踩坑：立刻写回，不要等会话结束。
3. **文件不存在**：不阻断。有内容要落盘时再 `--init` 或 `--set-section`（后者会先建骨架）。禁止为「空骨架」在每个 `task-new` 自动创建。
4. **默认涉及面**：仅作 `task-new` 涉及面初值（`taskctl new` 会预填骨架表）；本任务仍以 README 涉及面为准。
5. **禁止**写入密钥、token、内部未公开凭据。

```bash
python3 <this-skill>/scripts/taskctl.py notes
python3 <this-skill>/scripts/taskctl.py notes --init
python3 <this-skill>/scripts/taskctl.py notes --set-section 特殊要求 --body "- 验收必须带回归清单"
```

新建骨架含：概览、特殊要求、规格说明、默认涉及面、约定、手帐、踩坑。按实际删减，保持简洁。

## Checkout Gate（task 分支）

身份确定之后、**写入目标代码仓之前**，对必须仓绑定真实 checkout 并检出 `<prefix>-<slug>`。默认仍在 canonical checkout 工作；仅用户显式指定 `--worktree REPO=CHECKOUT` 时创建/采用 worktree。后续命令必须续用记录的 checkout。

**硬规则（只切目标仓）：**

1. 只对「本任务会修改」的 git 仓跑 `prepare-branches`（涉及面角色=必须，或本轮将写入的 OpenSpec/代码所在仓）
2. `--repo` 只列必须仓；禁止把 cwd / `.` 当作缺省填入（仅当工作区自身就是必须仓时才用 `.`）
3. 建议仓、排除仓、只读参考仓：不切
4. 无必须仓：跳过本 Gate（`--from-task` 得到空列表即成功），不要用 `.` 凑数
5. 写工作区 `tasks/` 记账不构成把工作区仓列入必须的理由（除非 `.` 本身被标为必须）

| 命令 | 何时跑 | 切哪些仓 |
|------|--------|----------|
| `task-new` | 涉及面必须仓已定后、`taskctl new` 之前 | 仅本轮梳理的必须仓（显式 `--repo path`）；无必须仓则跳过。骨架仍写入工作区 `tasks/`；Checkout Gate 仍只针对必须仓 |
| `task-explore` / `task-design` / `task-propose` / `task-apply` | `resolve` 成功后立刻 | `--from-task TNNNN`（README 涉及面必须仓） |
| `task-archive` | **不要**跑 `prepare-branches` | 归档用 `git-summary --repo <必须仓> --branch <prefix>-<slug>` |

- prefix：`feat`（默认）| `fix` | `chore` | `refactor`

```bash
# 已有 task：只切 README 涉及面必须仓
python3 <this-skill>/scripts/taskctl.py prepare-branches \
  --slug <slug> --prefix feat --from-task TNNNN [--dry-run]

# task-new（尚无 README）：显式列出必须仓
python3 <this-skill>/scripts/taskctl.py prepare-branches \
  --slug <slug> --prefix feat --repo path/to/target [--dry-run]

# 显式在 worktree 中开发；CHECKOUT 不存在时创建
python3 <this-skill>/scripts/taskctl.py prepare-branches \
  --slug <slug> --repo path/to/target \
  --worktree path/to/target=path/to/checkout
```

单仓且工作区自身就是目标时才加 `--repo .`。JSON `cwd_untouched` 仅作报告字段。

流程（脚本内，仅针对必须仓）：解析真实 checkout → 若 task 分支已被某 worktree 持有则路由到该 worktree → 已在目标分支则续作（允许 dirty）→ 否则脏仓门禁 → 检测默认分支 → 有 origin 则 fetch（失败即阻断）→ 从 `origin/<base>` 或 local-only base 创建/切换 task 分支。linked worktree 不先 checkout 可能被主工作树占用的 base。

若 JSON `needs_user_confirm=true`（脏工作区且不在目标分支、pull 失败等）：

1. **立即停止**，展示 `exit_markdown` / `user_actions` / `dirty_porcelain`
2. 等用户明确指示（提交清理 / 允许 `--skip-dirty` / 中止）
3. **禁止** Agent 自行 stash、reset --hard、checkout -f

可用 `--base` 覆盖默认分支；不自动 push。`--from-task` 成功或部分成功后自动把 canonical repo / checkout / worktree / branch / base 写入 README。

## 改码建议（非硬约束）

写代码时的**倾向**（主要是 `task-apply`；propose / design 定范围时也可对照），不是 MUST，也不是门禁。用户口头、设计文档或工作区笔记另有取舍时以那为准。不要为了「更干净」扩大本轮范围。

### 先定模式

动手前用一句话判定本轮是哪一种。**未点名重新设计时，按修复或新增做，不要默默升级。** 模式不清先问一句。修复里发现「其实该换模型」→ 停下来建议 `{{slash:task-design}}` / 请用户确认，不要在修复 diff 里完成重新设计。

| 模式 | 典型信号 | 建议怎么用 |
|------|----------|------------|
| **修复** | 纠错、去掉多余、补漏；契约语义不变 | 只动被指出的缺陷面；做减法；相邻旧约定保持原样 |
| **新增** | 在既有结构上加能力 | 新路径写成规范形态；旧路径不顺手改写、不对齐 |
| **重新设计** | 用户明确要求，或已走 `task-design` 且方案已定 | 可以换抽象、动边界；仍选最窄表示、一条语义一条路径；未列入设计范围的保持原样 |

### 六条倾向

1. **做减法。** 每一轮只去掉被指出的多余，不要用另一种抽象去替换。
   - 修复：最贴这条。删多余即可，不要借机引入新层。
   - 新增：新代码保持薄；不要借新增把旧代码换成新抽象。
   - 重新设计：可以替换抽象，但替换必须是本轮设计结论，不是「顺便」。
2. **规范形态写在边界上。** 按线上真实值写入；比较走精确路径，不在读侧做多路兜底。
   - 修复：若缺陷来自读侧兜底，收紧那条路径，不要再加一种兼容。
   - 新增：入口写成规范形态，内部只认一种形状。
   - 重新设计：可以重定规范形态，定完只留一条读写路径。
3. **隔离优先于宽容。** 坏项可跳过时，不要再给全量输入做兼容解析。
   - 修复 / 新增：坏数据跳过或拒绝；不要为「也能跑」给整包加兼容。
   - 重新设计：容错应是隔离策略（跳过 / 拒绝），不是全量模糊解析。
4. **不碰非修复面。** 相邻的旧约定不是本轮缺陷，就保持原样。
   - 修复：最贴这条。
   - 新增：新代码可以走新约定，但不要改写相邻旧代码去对齐。
   - 重新设计：可以动相邻面，但应已写进设计范围。
5. **选最窄的表示。** 需要什么类型就用什么类型，避免先收成更宽的形状再转回去。
   - 三种模式都适用。修复尤其不要为修一个窄问题引入更宽的中间类型。
6. **一条语义一条路径。** 同一判断写两遍三遍，说明还没选定规范形态。
   - 修复：本轮只修其中一处时，不要顺手「统一」成新抽象（那是重新设计）。
   - 新增：新判断只写一条路径。
   - 重新设计：正好用来选定规范形态并收成一条路径。

## 各命令职责（摘要）

**每个命令开始时**先加载工作区笔记（见上）。`exists=true` 则遵守其中硬约束。

### task-new

**抽取本条需求（先做，再决定是否追问）**

同一条消息里，`{{slash:task-new}}` 之后的正文、冒号/引号后的描述、以及任何「要改什么」的句子，都是需求。command / skill 的流程套话（MUST 先读、输入栏、下一步桥接、本段说明）**不是**需求，也**不是**「缺少输入」的理由。

1. 能用一句话概括「要做什么」→ **足够，立刻创建**。自行推导 title 与 kebab-case slug（英文语义、短、稳定）。用户给了 slug 才用用户的。细节不全（哪些文件、怎么实现、验收怎么写）写入「现状缺口」，**禁止**停下来要用户重述需求或确认 slug。
2. 只有本条**完全没有主题**才追问一句「要做什么」。例如：光秃 `{{slash:task-new}}`、只有「帮我建个任务」、或整段都是流程说明且没有任何改动对象。不要要 slug，不要给填写模板，不要把「没写『需求描述：』标签」当成信息不足。

然后：

1. `taskctl notes`：默认涉及面作为涉及面初值；特殊要求 / 规格写入本任务时仍须遵守
2. 按上面规则得到 title / slug（不要追问）
3. 梳理涉及面（代码库表：必须=会修改 / 建议=只读 / 排除=无关）。笔记里的默认涉及面可作起点，按本任务修正
4. 对照目标梳理**现状缺口**（已有 vs 仍缺；信息/实现/资产/配置/依赖确认）
5. **Checkout Gate**：仅对必须仓 `prepare-branches --slug <slug> --repo <path>`（可重复 `--repo`；无必须仓则跳过）。仅当工作区自身就是必须仓时才传 `.`。`needs_user_confirm` 则停等用户。返回后把 worktree / 改动仓 / 分支记入稍后填写的「工作上下文」
6. `taskctl new --title ... [--slug ...]` 分配 ID、建骨架 README（status=`draft`）、更新 INDEX（写在工作区 `tasks/`；Checkout Gate 仍只针对必须仓）。有把握的 slug 显式传入；否则 `--title` 即可（ASCII 足够时 CLI 会推导）
7. Agent 补全概述/背景/目标/现状缺口/涉及面/**工作上下文**/验收标准（遵守工作区笔记硬约束）。Checkout Gate 已跑则立刻把 worktree / 改动仓 / 分支写入工作上下文
8. 输出 ID、路径、分支、涉及面、工作上下文、现状缺口摘要、下一步桥接（缺口偏方案 → explore；范围已清且无需架构决策 → propose）

### task-explore

1. `taskctl resolve` Gate（本条或本会话上文有明确 `TNNNN` 则显式传；否则 `--infer` 且 `--hint` 带上文编号；`needs_confirm` 则停）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切必须仓；无必须仓则跳过）。`needs_user_confirm` 则停。返回后立刻更新 README「工作上下文」
3. 加载 `task.openspec`、README 与 `workflow_notes`
4. **委托** `openspec-explore`：把 task 概述/涉及面与工作区笔记作为探索上下文；不写业务代码
5. 将结论要点写回 README「变更记录」或「方案笔记」；若原 status 为 `draft` → `taskctl set-status <id> exploring`
6. 输出探索摘要 + 桥接：仍有架构分叉 / 新子系统 / 用户要全面设计 → `{{slash:task-design}}`；范围已清、路径唯一 → `{{slash:task-propose}}`

### task-design

可选。无 task 则先 `{{slash:task-new}}`。方法细节读 skill `task-design`。

1. `taskctl resolve` Gate（本条或本会话上文有明确 `TNNNN` 则显式传；否则 `--infer` 且 `--hint` 带上文编号；`needs_confirm` 则停）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切必须仓；无必须仓则跳过）。`needs_user_confirm` 则停。返回后立刻更新 README「工作上下文」
3. 加载 README 概述、explore 结论
4. **只写入** `<taskRoot>/design/`（`README.md` 索引 + 归档落点表 + 设计正文）。**禁止**此时写 `docs/design/`、ADR、knowledge。若本轮是重新设计，写清新的规范形态与边界（对照「改码建议」），未列入范围的旧约定保持原样
5. 在 task README「设计文档」记录文件与计划落点；`taskctl set-status <id> designed`
6. 输出 staged 路径、归档落点表、未决问题、`{{slash:task-propose}} TNNNN` 桥接

跳过条件：explore 后改动局部、可行路径只有一条、无跨模块契约。跳过则 status 保持 `exploring`，直接 propose。

### task-propose

1. `taskctl resolve` Gate（本条或本会话上文有明确 `TNNNN` 则显式传；否则 `--infer` 且 `--hint` 带上文编号；`needs_confirm` 则停）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切将写入 OpenSpec 的必须仓）。`needs_user_confirm` 则停（OpenSpec 写进哪个仓，就只在那个仓切 task 分支）。返回后立刻更新 README「工作上下文」
3. 若存在 `design/`，把它当作提案输入（推荐路径、接口契约、未决问题）；不要丢弃已做的设计结论
4. 根据涉及面决定 change 落点：单仓 → 该仓 `openspec/`；跨仓/工作区级配置 → 工作区 `openspec/`；可多个 change。若会写工作区，`.` 必须作为「必须」仓通过 Checkout Gate
5. 对每个计划中的 change **委托** `openspec-propose`。能判断时在 proposal / tasks 里标明本轮是修复 / 新增 / 重新设计，供 apply 对照「改码建议」
6. 将全部 change 的名称、**canonical 仓库**、仓内相对路径和 store 写入 README「关联 OpenSpec」；`taskctl set-status <id> proposed`
7. 输出 change 列表、分支与 `{{slash:task-apply}} TNNNN` 桥接

### task-apply

1. `taskctl resolve` Gate（本条或本会话上文有明确 `TNNNN` 则显式传；否则 `--infer` 且 `--hint` 带上文编号；`needs_confirm` 则停）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切必须仓，不要用 `.` 凑数）。`needs_user_confirm` 则停等用户（已在目标分支则跳过）。返回后立刻更新 README「工作上下文」（多仓逐行；标明是否 worktree）
3. `taskctl execution-context <id>`；若 OpenSpec 为空中止并建议 propose。读取已有 `progress.md` 与各 change checkbox，严格使用每个 target 的 `planning_root` / store，不得从当前 cwd 猜
4. **实施前 checkpoint**：`taskctl checkpoint <id> --phase implementing --change ... --current-task ...`
5. 对每个未完成 change 委托 `openspec-apply-change`。改码前先定模式（修复 / 新增 / 重新设计），对照「改码建议」（均为倾向）。每完成一个 checkbox，立刻再次 checkpoint；然后继续下一项，直到全部完成或阻塞
6. 暂停、错误或用户中断前 MUST checkpoint `--phase blocked`（含 blocker/next）；进入测试时 checkpoint `testing --verification ...`；全部完成 checkpoint `done`
7. 输出：真实 checkout/分支表、各 change 进度、checkpoint 路径、交接（续作：`{{slash:task-apply}} TNNNN`）

### task-archive

1. `taskctl resolve` Gate（本条或本会话上文有明确 `TNNNN` 则显式传；否则 `--infer` 且 `--hint` 带上文编号；`needs_confirm` 则停）
2. `taskctl execution-context <id>`，读取各 target 的 `remaining_kind` / `openspec_remaining`。**先分类剩余 checkbox，再决定是否委托 `openspec-archive-change`：**
   - `remaining_kind=none`：在各 target 的 planning root/store 依次委托 `openspec-archive-change`
   - `remaining_kind=verification_only`：**MUST 向用户确认**是否继续 archive。列出剩余测试/验证项与完成数（如 14/18）。禁止把「未完成」直接当成结案停止，也禁止未确认就归档。用户确认「继续归档」或本条已写「强行合并 / `--force-merge`」后再委托 `openspec-archive-change`，随后 `taskctl archive <id> --force-merge`
   - `remaining_kind=implementation`：停止并列出未完成实现项。仅当用户明确「强行合并」时才用 `--force-merge` 继续
   任一 change 归档或 delta sync 失败即停止，不得继续 task 归档
3. **晋升设计文档**（若 `<taskRoot>/design/` 存在）：按 `design/README.md` 归档落点表，把文档复制到目标仓正式位置（`docs/design/<domain>/`、ADR、knowledge）；更新该仓 INDEX/README 交叉引用并核对链接。落点不明则停下来问，不要发明目录。`design/` **原件保留**，随 task 目录归档作快照。无 `design/` 则跳过
4. 按 execution-context 对每仓运行 `git-summary --repo <canonical> --checkout <canonical>=<checkout> --branch <记录分支> --base <记录基线>`，同时纳入提交、staged 与 working-tree diff
5. `taskctl archive <id>` 机械校验：无活跃 OpenSpec、验收全勾选、progress 有验证证据、checkout clean。只剩测试/验证时 CLI 亦会 `needs_confirm`（退出码 2）。确需跳过时使用对应显式 `--allow-*` 或 `--force-merge`（强行合并未完成 OpenSpec），覆盖原因自动写入 `changes.md`
6. archive 内置 status→archived，并在移动/INDEX 写入失败时回滚
7. 桥接：列出已晋升文档路径

## 产物字段

### `.task-workflow.md`（工作区根）

跨任务仍有效的特殊要求、规格说明、默认涉及面。由 `taskctl notes` 读写；不是某个 task 目录的附件。

### changes.md（task-archive）

涉及代码库、是否 worktree、改动摘要、提交记录、文件变更（按仓库）、关联 OpenSpec/PR、备注。

### design/（task-design）

仅存在于 task 目录：`design/README.md`（索引 + 归档落点表）与一篇或多篇设计正文。归档前不是仓库正式文档；晋升规则见 task-archive。

### 工作上下文（task README）

实际执行环境：git worktree 是否使用及路径、实际改动的代码库（多仓逐行）、各仓分支与基线。Checkout Gate 后与环境变化时立刻更新；不替代「涉及面」。

### progress.md（task-apply 必填）

由 `taskctl checkpoint` 维护：阶段 `implementing|testing|blocked|done`、当前 change/task、OpenSpec checkbox 进度、本轮完成、验证证据、Git 快照、阻塞与下一步。MUST NOT 手工攒到会话结束；每项完成或暂停时立即写。

## 桥接块（各 command 输出末尾）

```
- 方案未定 → {{slash:task-explore}} TNNNN
- 复杂 / 多方案 → {{slash:task-design}} TNNNN
- 范围已清 → {{slash:task-propose}} TNNNN
- 契约就绪 → {{slash:task-apply}} TNNNN
- 交付完成 → {{slash:task-archive}} TNNNN
```
