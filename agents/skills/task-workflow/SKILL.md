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
| `new --slug <slug> [--title ...] [--date YYYY-MM-DD]` | 分配 `TNNNN`、建目录与 README 骨架、更新 INDEX | 0 |
| `archive <query> [--allow-missing-changes]` | status→archived、移至 `tasks/archive/`、更新 INDEX | 0 / 2 |
| `repo-roots <path> [...]` | 解析为去重后的 git 根（工作区相对路径；`.` = 工作区自身，仅当工作区就是目标仓时使用） | 0 / 1 |
| `scope-repos <query> [--cwd ...]` | 解析 README 涉及面；`checkout` 仅为角色=必须的仓（不含 cwd） | 0 / 2 |
| `prepare-branches --slug <slug> [--from-task <query>] [--repo <path>]` | Checkout Gate：只对必须修改的目标仓做脏仓门禁 + `fetch`/基线/`checkout -b <prefix>-<slug>` | 0 / 1 / 2 |
| `git-summary --repo <path> [--branch ...] [--base ...]` | 只读 log/diff，产出 `changes.md` 素材（含 `markdown`） | 0 / 1 |
| `notes` | 读写工作区根 `.task-workflow.md`（`--init` / `--from-file` / `--set-section`） | 0 / 1 |

- stdout：**仅 JSON**（`ok` / `result` / `task` 或 `exit_markdown`）。
- stderr：一行人读摘要（如「当前任务：T0002 — path」）。
- `resolve`/`set-status`/`archive` 在零/多命中或 `needs_confirm` 时打印 `exit_markdown`，**中止主流程**，等待用户选择。
- `new` 只建骨架；概述/现状缺口/涉及面/验收等正文仍由 Agent 填写。
- `archive` 默认要求已有 `changes.md`（OpenSpec 归档与正文结论先做完）。
- `prepare-branches`：身份确定后、**写入目标代码仓之前**跑（不要拖到 `task-apply`）。**只切本任务需要修改的目标 git 仓**；解析远端默认分支（`origin/HEAD`，未必是 main/master）→ `fetch` → checkout 默认分支 → `pull --ff-only` → `checkout -b <prefix>-<slug>`。优先 `--from-task TNNNN`（从 README 涉及面取角色=必须的仓）。`--repo` 仅用于显式列出那些必须仓（task-new 时尚无 README 时）。**禁止**把 cwd / `.` 当作缺省目标：当前所在仓若不是必须修改的目标仓，**不得**切换。无必须仓则跳过（`skipped=no_target_repos`），不要用 `.` 凑数。已在目标分支则跳过（**允许脏工作区**，视为续作）。脏仓且不在目标分支 / pull 失败 → `needs_user_confirm` + `user_actions` + `exit_markdown`，**停下来让用户确认**；仅用户明确同意后才可 `--skip-dirty`。支持 `--dry-run`；不 `push`；禁止擅自 `stash`/`reset --hard`/`checkout -f`。
- `scope-repos`：只读解析涉及面。`checkout` = 必须仓路径；建议/排除不在内；cwd 只出现在 `cwd_*` 报告里，不会加入 checkout。
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

除 `{{slash:task-new}}` 外，所有 task command **第一步 MUST** 调用 `resolve`。有编号/路径时传入 query；**未指定时省略 query 并带上下文做自动推断**：

```bash
# 显式
python3 <this-skill>/scripts/taskctl.py resolve <TNNNN|slug|path> --command <当前命令名>

# 未指定：自动推断（把用户原话放进 --hint）
python3 <this-skill>/scripts/taskctl.py resolve --infer --command <当前命令名> \
  --hint "<用户消息原文>" [--cwd "$PWD"] [--git-branch "<当前分支>"]
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
- **禁止**仅凭模糊对话印象或 OpenSpec change 名在未跑 `resolve` 的情况下擅自选定 task。

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
- **涉及面**：本任务会**修改**的目标仓库相对路径 / 是否跨仓（task-new 梳理；后续可修正）。角色=必须 才会被 Checkout Gate 切分支。当前工作目录、只读参考仓不要写进必须。
- **关联 OpenSpec**：change 名与路径列表（task-propose 写入；可多个；`taskctl resolve` 会解析该表）
- **设计文档**（task-design 写入）：`design/` 下文件与归档落点表；未做设计则保持「尚无」
- 不得含明文密钥或数据库凭证；需要时写环境变量名 `$VAR_NAME`

## 路径与仓库

- 工作区：含 `tasks/` 的目录（`taskctl --root` 的探测目标）
- 目标 git 仓：工作区相对路径，且必须是本任务会写入的代码仓。**不要**因为 cwd 是某个 git 仓就把它当作目标
- `.` 的含义：工作区 git 根本身。仅当工作区就是要改的那个仓时才用 `--repo .`（典型单仓项目）。多仓工作区 / 当前仓与任务无关时，**禁止**传 `.`
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

身份确定之后、**写入目标代码仓之前**，对**必须修改的目标仓**检出 `<prefix>-<slug>`（用 slug，不用带 T 前缀的目录名）。不要等到 `task-apply` 才建分支：OpenSpec 与实现写进哪个仓，就只在那个仓切 task 分支。

**硬规则（只切目标仓）：**

1. 只对「本任务会修改」的 git 仓跑 `prepare-branches`（涉及面角色=必须，或本轮将写入的 OpenSpec/代码所在仓）
2. **禁止**把 cwd / `.` 自动加入 `--repo`。当前所在仓若不在必须列表里，**MUST NOT** checkout，保持原分支
3. 建议仓、排除仓、只读参考仓：不切
4. 无必须仓：跳过本 Gate（`--from-task` 得到空列表即成功），不要用 `.` 凑数
5. 写工作区 `tasks/` 记账不构成切换工作区仓的理由（除非 `.` 本身被标为必须）

| 命令 | 何时跑 | 切哪些仓 |
|------|--------|----------|
| `task-new` | 涉及面必须仓已定后、`taskctl new` 之前 | 仅本轮梳理的必须仓（显式 `--repo path`）；无必须仓则跳过。骨架仍写入工作区 `tasks/`，不因此切工作区 |
| `task-explore` / `task-design` / `task-propose` / `task-apply` | `resolve` 成功后立刻 | `--from-task TNNNN`（README 涉及面必须仓）。cwd 无关则不动 |
| `task-archive` | **不要**跑 `prepare-branches` | 归档用 `git-summary --repo <必须仓> --branch <prefix>-<slug>` |

- prefix：`feat`（默认）| `fix` | `chore` | `refactor`

```bash
# 已有 task：只切 README 涉及面必须仓
python3 <this-skill>/scripts/taskctl.py prepare-branches \
  --slug <slug> --prefix feat --from-task TNNNN [--dry-run]

# task-new（尚无 README）：显式列出必须仓，不要写 cwd
python3 <this-skill>/scripts/taskctl.py prepare-branches \
  --slug <slug> --prefix feat --repo path/to/target [--dry-run]
```

单仓且工作区自身就是目标时才加 `--repo .`。JSON 里 `cwd_untouched=true` 表示当前仓未被切换。

流程（脚本内，仅针对传入的必须仓）：已在目标分支则跳过（**允许脏工作区**，视为续作）→ 否则脏仓门禁 → 检测默认分支（`origin/HEAD` / `remote show`，**不假设 main**）→ `fetch` → checkout 默认分支 → `pull --ff-only` → `checkout -b`（或切到已有同名分支）。无关仓不进入该流程。

若 JSON `needs_user_confirm=true`（脏工作区且不在目标分支、pull 失败等）：

1. **立即停止**，展示 `exit_markdown` / `user_actions` / `dirty_porcelain`
2. 等用户明确指示（提交清理 / 允许 `--skip-dirty` / 中止）
3. **禁止** Agent 自行 stash、reset --hard、checkout -f

可用 `--base` 覆盖默认分支（记入 README）；不自动 `git push`。

## 各命令职责（摘要）

**每个命令开始时**先加载工作区笔记（见上）。`exists=true` 则遵守其中硬约束。

### task-new

1. `taskctl notes`：默认涉及面作为涉及面初值；特殊要求 / 规格写入本任务时仍须遵守
2. 从描述推导 `slug`；不足则追问
3. 梳理涉及面（代码库表：必须=会修改 / 建议=只读 / 排除=无关）。当前仓若不是修改目标，标排除或不要列入必须；笔记里的默认涉及面可作起点，按本任务修正
4. 对照目标梳理**现状缺口**（已有 vs 仍缺；信息/实现/资产/配置/依赖确认）
5. **Checkout Gate**：仅对必须仓 `prepare-branches --slug <slug> --repo <path>`（可重复 `--repo`；无必须仓则跳过）。**不要**传 cwd / `.`，除非工作区自身就是必须仓。`needs_user_confirm` 则停等用户
6. `taskctl new --slug ... --title ...` 分配 ID、建骨架 README（status=`draft`）、更新 INDEX（写在工作区 `tasks/`，不因此切工作区仓）
7. Agent 补全概述/背景/目标/现状缺口/涉及面/验收标准（遵守工作区笔记硬约束）
8. 输出 ID、路径、分支、涉及面、现状缺口摘要、下一步桥接（缺口偏方案 → explore；范围已清且无需架构决策 → propose）

### task-explore

1. `taskctl resolve` Gate（有 ID 显式传；否则 `--infer --hint ...`；`needs_confirm` 则停）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切必须仓；无必须仓则跳过；当前仓无关则不动）。`needs_user_confirm` 则停
3. 加载 `task.openspec`、README 与 `workflow_notes`
4. **委托** `openspec-explore`：把 task 概述/涉及面与工作区笔记作为探索上下文；不写业务代码
5. 将结论要点写回 README「变更记录」或「方案笔记」；若原 status 为 `draft` → `taskctl set-status <id> exploring`
6. 输出探索摘要 + 桥接：仍有架构分叉 / 新子系统 / 用户要全面设计 → `{{slash:task-design}}`；范围已清、路径唯一 → `{{slash:task-propose}}`

### task-design

可选。无 task 则先 `{{slash:task-new}}`。方法细节读 skill `task-design`。

1. `taskctl resolve` Gate（同上，可推断）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切必须仓；无必须仓则跳过；当前仓无关则不动）。`needs_user_confirm` 则停
3. 加载 README 概述、explore 结论
4. **只写入** `<taskRoot>/design/`（`README.md` 索引 + 归档落点表 + 设计正文）。**禁止**此时写 `docs/design/`、ADR、knowledge
5. 在 task README「设计文档」记录文件与计划落点；`taskctl set-status <id> designed`
6. 输出 staged 路径、归档落点表、未决问题、`{{slash:task-propose}} TNNNN` 桥接

跳过条件：explore 后改动局部、可行路径只有一条、无跨模块契约。跳过则 status 保持 `exploring`，直接 propose。

### task-propose

1. `taskctl resolve` Gate（同上，可推断）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切将写入 OpenSpec 的必须仓；当前仓无关则不动）。`needs_user_confirm` 则停（OpenSpec 写进哪个仓，就只在那个仓切 task 分支）
3. 若存在 `design/`，把它当作提案输入（推荐路径、接口契约、未决问题）；不要丢弃已做的设计结论
4. 根据涉及面决定 change 落点：单仓 → 该仓 `openspec/`；跨仓/工作区级配置 → 工作区 `openspec/`；可多个 change
5. 对每个计划中的 change **委托** `openspec-propose`
6. 将全部 change 名与路径写入 README「关联 OpenSpec」；`taskctl set-status <id> proposed`
7. 输出 change 列表、分支与 `{{slash:task-apply}} TNNNN` 桥接

### task-apply

1. `taskctl resolve` Gate（同上，可推断）
2. **Checkout Gate**：`prepare-branches --slug <slug> --from-task <id>`（只切必须仓，不要 `repo-roots` 当前仓或 `.`）。`needs_user_confirm` 则停等用户（已在目标分支则跳过）
3. 若 `task.openspec` 为空 → 中止并建议 `{{slash:task-propose}}`
4. 对每个未完成 change **委托** `openspec-apply-change`；用户可指定子集
5. `taskctl set-status <id> in_progress`（或 `blocked`）；可选覆盖写 `progress.md`
6. 输出：分支表、各 change 进度、交接（续作：`{{slash:task-apply}} TNNNN`）

### task-archive

1. `taskctl resolve` Gate（同上，可推断）
2. 对 README 中仍活跃的关联 change，依次 **委托** `openspec-archive-change`；已归档则跳过；用户确认后可跳过失败项
3. **晋升设计文档**（若 `<taskRoot>/design/` 存在）：按 `design/README.md` 归档落点表，把文档复制到目标仓正式位置（`docs/design/<domain>/`、ADR、knowledge）；更新该仓 INDEX/README 交叉引用并核对链接。落点不明则停下来问，不要发明目录。`design/` **原件保留**，随 task 目录归档作快照。无 `design/` 则跳过
4. `taskctl git-summary --repo <必须仓路径> [--branch feat-<slug>]` 取素材 → 人工核对后写入 `changes.md`（可补 PR/备注；写明已晋升的设计路径；不要对无关仓采摘要）
5. 验收未勾选须警告并获确认
6. `taskctl archive <id>`（移动目录 + INDEX；内置 status→`archived`）
7. 桥接：列出已晋升文档路径

## 产物字段

### `.task-workflow.md`（工作区根）

跨任务仍有效的特殊要求、规格说明、默认涉及面。由 `taskctl notes` 读写；不是某个 task 目录的附件。

### changes.md（task-archive）

涉及代码库、改动摘要、提交记录、文件变更（按仓库）、关联 OpenSpec/PR、备注。

### design/（task-design）

仅存在于 task 目录：`design/README.md`（索引 + 归档落点表）与一篇或多篇设计正文。归档前不是仓库正式文档；晋升规则见 task-archive。

### progress.md（task-apply 可选）

元信息（时间、阶段 `implementing|testing|blocked`）、关联 OpenSpec、本轮完成、累计进展、Git 快照（只读）、阻塞、下一步。
MUST NOT 在采集快照时 stash/reset/force checkout；只读引用 change 内 `tasks.md`，不修改 OpenSpec 工件。

## 桥接块（各 command 输出末尾）

```
- 方案未定 → {{slash:task-explore}} TNNNN
- 复杂 / 多方案 → {{slash:task-design}} TNNNN
- 范围已清 → {{slash:task-propose}} TNNNN
- 契约就绪 → {{slash:task-apply}} TNNNN
- 交付完成 → {{slash:task-archive}} TNNNN
```
