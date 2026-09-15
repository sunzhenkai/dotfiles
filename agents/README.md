# Shared agent skills

跨 Cursor / Kiro / OpenCode / Codex / Kimi Code / Pi / ZCode / Claude Code 等工具的 **skills 唯一真相源**。

## 统一入口（推荐）

**边界**：`agents` 负责聚合安装计划与共享 skills 同步；单工具模块只安装各自的 CLI。

```shell
dotf agents -i                 # 计划展开为各 agent CLI 的独立 install 动作
dotf cursor -i                 # 仅安装 Cursor CLI
dotf agents -c                 # 聚合同步 skills（~/.agents/skills → Kiro → Claude Code）+ 全局 AGENTS.md
dotf skills -i <name>          # npx skills 按需安装；先匹配 skills.yaml 的 group，再匹配 skill id，最后透传给 npx；-g 全局 / --project 项目 / -y 跳过询问
dotf skills -r <skill-name>    # 移除已安装 skill（省略名称进入 npx skills 交互式移除；短名同走映射）
dotf agents skill apply <id>   # 写入本机 overlay Desired Set 并 sync（含该 id 的来源）
dotf agents skill remove <id>  # 停用并 prune owned 且未漂的目标（不改仓库）
dotf agents skill apply <id> --on-conflict=backup  # 先备份本机漂移再覆写
dotf agents -d                 # L0 诊断
dotf agents -d --deep          # L0 + agents L1 深度诊断
dotf agents -d --deep --json   # 深度诊断 JSON（凭据脱敏）
dotf agents -cd                # 先同步再诊断
scripts/modules/agents/sync.sh all
PYTHONPATH=scripts python3 src/agents/doctor.py
```

## 布局

```text
agents/
  skills/<skill-id>/SKILL.md       # 一手 skill 源（frontmatter 渲染后分发）
  skills/<skill-id>/references/    # 可选：随 skill 原样分发（不做渲染/替换，字节一致）
  skills/<skill-id>/scripts/       # 可选：随 skill 原样分发（helper CLI / 审计脚本）
  instructions/AGENTS.md           # 全局 agent 指令（用户级，跨项目）
  instructions/install.yaml        # 安装目标（~/.agents、Codex、Cursor rules、Claude Code）
  skills.yaml                      # 全量 Skill 编目（按 group；一手 + 第三方；唯一真相源）
  skills.lock.yaml                 # 第三方 skill 的严格审计锁（revision/hash/license/audit）
  vendors/<tool>/                  # 工具专属 settings / 人格 / 生成物
  env/                             # profiles / env 检查 / security 真相源
  README.md
```

工具专属 settings、OpenCode 人格等放在 `agents/vendors/<tool>/`。  
env / security 真相源在 `agents/env/`，由单一脚本包 `src/agents/` 编排，不要手写多源漂移。

## Frontmatter（源）

**Skill** 至少包含：

```yaml
---
id: my-skill
name: my-skill
description: ...
---
```

## 脚本与模型的分工（写 skill 脚本前必读）

skill 自带脚本（`scripts/`）只做**确定性**的事：读写结构化文件、算 ID、跑 git、校验格式、汇报事实。**理解自然语言、判断意图与性质是模型的职责**，不要外包给正则。

- **禁止**让脚本从用户消息 / 自由文本里「挖」需求、意图或语义分类。模型先归纳，再把结论**作为参数**传给脚本（如 `--title` / `--slug`）。
- **禁止**要求 Agent 把渲染后的消息逐字转存给脚本解析。模型无法可靠复现自己的输入，漏抄是静默的，脚本无从校验，最后会把转录失误变成对用户的错误追问。
- **禁止**用关键词表决定门禁强度（「这条待办算不算测试项」这类）。脚本列事实与原文，模型说明判断，**用户拍板**。
- 需要按宿主（Cursor / Kiro …）渲染格式加解析分支时，说明设计错了：换成模型理解 + 参数传入，而不是再加一条围栏规则。
- 正例：`audit-skill.sh` 只报命中行，由 Agent 复核、用户豁免。启发式来源一律交用户确认，不要让脚本替用户做语义判断。

## 语言

skills 面向用户的说明与输出默认 **简体中文**。
id、slash 命令、路径、代码、状态值、CLI flag 与既成术语（如 OpenSpec、Gate、Blocker）保持原文，不要逐词硬翻。
`en-chat` 除外（陪练回复用英语）。`references/` 原样分发，不要求翻译。

## 占位符

正文里需要 slash 命令时，写：

```text
{{slash:opsx-apply}}
```

同步时统一渲染为 `/opsx-apply`（Kiro 目标例外，见下文）。

## 同步

skills 同步到三个 runtime layout（`src/agents/layouts.py` 是目标清单的唯一真相源）：

| layout | 目标 | 渲染 |
|---|---|---|
| shared | `~/.agents/skills/<id>/` | `{{slash:x}}` → `/x` |
| kiro | `${KIRO_HOME:-~/.kiro}/skills/<id>/` | 同上，并在末尾补 `$ARGUMENTS` |
| claude | `~/.claude/skills/<id>/` | 同 shared |

含 `references/`、`scripts/` sidecar，原样字节分发。Kiro CLI 不读 `~/.agents/skills`，因此额外托管一份镜像；`KIRO_HOME` 必须指向 HOME 内的真实目录，避免越过 dotf 的 HOME 写入边界。Claude Code 从 `~/.claude/skills/` 读个人级 skill，并且自己消费 `$ARGUMENTS`（无占位符时按 `ARGUMENTS: <value>` 追加），所以 claude 目标不做 Kiro 式的显式注入；`synced` 是 Claude Code 的保留目录名，编目里用它会 fail closed。

同一入口还会安装全局 `AGENTS.md`（跨项目默认指令，不含 skill 目录）：`~/.agents/AGENTS.md`、`~/.codex/AGENTS.md`、Cursor 用户级 `~/.cursor/rules/00-dotf-global.mdc`，以及 Claude Code 的 `~/.claude/CLAUDE.md`（Claude Code 只读该文件名，不读 `AGENTS.md`）。源在 `agents/instructions/`。**不要手改**这些安装产物。漂移在 doctor 的 `instructions` 段与 TUI 的 Status / Conflicts 面板可见。

本机 Skill Desired Set = `agents/skills.yaml` 编目内非 optional id ∪ overlay `enabled_skills` − `disabled_skills`。**没有 default 字段**：编目内即默认全量安装；成员可写 `- id: <id>` + `optional: true` 映射表示"默认不装、可经 overlay / `agents skill apply` 按需启用"；不想保留就把该条目注释掉（注释即不在编目内，不自动装、也不能经 overlay / `agents skill apply` 引用）。未锁定第三方与 OpenSpec 生成的 `openspec-*` 不能进入 Desired Set。apply / remove 只改 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/`，不改仓库编目 / lock。

`agents skill apply/remove <id>` 与 `agents -c` 一样会补齐该 id 所属来源：一手 id 走仓库目录；第三方 id 追加一次锁定获取（`acquire_all` 按 lock 条目逐条 fetch，所以一手 apply 不会走网络）。OpenSpec 的 `openspec-*` 只由 `agents -c` 安装。

一手 skill 来自 `agents/skills/`，并在 `agents/skills.yaml` 的 `dotfiles` 组编目（`type: first-party`）；未编目的目录会在校验时 fail closed。第三方 skill 在同一编目里按来源分组成 `type: third-party`（`source: github`/`registry` + `package`），由严格锁 `agents/skills.lock.yaml` 固定 revision/hash/license/audit，经同一入口安装到全部 layout。OpenSpec 阶段 skill **不**放进 `agents/skills/`：同一入口调用本机 `openspec init --tools agents`，把 CLI 生成的 `openspec-*` 装到全部 layout。缺少 openspec CLI 时只警告，不阻断一手 skill 同步；技能集合跟随用户的 OpenSpec profile / workflows。

### 冲突

冲突 = owned 目标的内容或 mode 已不等于上次受管 hash（本机改过）。默认 **fail closed**：sync 保留该文件、报出具体目标与原因，`RESULT` 的 reason 形如 `skill sync failed: skills: service-manager/SKILL.md: owned target was modified locally`。

第三方 skill 的 identity 内嵌整份 lock 的 digest，因此新增/删除任一 lock 条目都会改写所有第三方 identity。若目标仍由本系统拥有、且字节已等于新 lock 固定的内容，sync 会直接重记 identity（无备份、无需 flag），不报冲突；只有字节真的不同（本机漂移）才继续 fail closed。

要从漂移里恢复，用 `--on-conflict=backup`：先把当前内容备份到 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/<home 相对路径>`，再写入受管版本。

```bash
dotf agents skill apply codebase-design --on-conflict=backup
dotf agents -c --on-conflict=backup
```

该开关只解除"owned 目标漂移"这一类冲突。不安全类型（symlink 等）、manifest 不可解析、所有权不符、无所有权目标、越界目标**永远** fail closed；`deconfig` / `uninstall` / `remove` 的 prune 方向也永远 fail closed，不受该开关影响。

```bash
# 同步 skills（三个 layout）+ 全局 AGENTS.md
scripts/modules/agents/sync.sh all

# 只预览
scripts/modules/agents/sync.sh --dry-run

# 也可用配置入口
scripts/lib/dispatch_config.sh agents
```

共享 sync：`dotf agents -c`。单工具 `dotf <tool> -c` 只应用 vendor 配置，不隐式全量 sync。
本仓库不声明 LLM provider / 模型 / 密钥（见 `docs/adr/0017-remove-ai-provider-config.md`），vendor 配置只含工具行为与中文人格等稳定内容。

**不要手改** `~/.agents/skills/`、`${KIRO_HOME:-~/.kiro}/skills/` 或 `~/.claude/skills/` 里由本系统生成的文件；一手 skill 请改 `agents/skills` 并在 `agents/skills.yaml` 编目后重新 sync，第三方 skill 请改 `agents/skills.yaml` + `agents/skills.lock.yaml`，OpenSpec 阶段 skill 请升级 CLI 后重新 `dotf agents -c`。已经手改过又想要受管版本，用 `--on-conflict=backup`（先备份再覆写）。

已归档的 skill 移到 `agents/skills-archive/<name>/`（保留生产内容，不入编目、不参与安装，恢复方式见该目录 `README.md`）。

## 示例条目

仓库自带：`commit-push`、`en-chat`、`repo-manager`、`role-based-reviewer`、`service-manager`、`skills-store`、`skill-evolver`（从多次真实执行进化已有 Skill：候选 patch → 验证 → 晋升/拒绝，不直接改生产稿，也不在每次任务后自动改）、`skill-upgrader`（把已有 `SKILL.md` 一次性升级为带 `examples/` `evals/` `experience/` 的自进化结构，不伪造历史、不按单次失败改正文；真正改生产稿仍走 `skill-evolver`）、`pretty-view-html`（将已有内容做成 HTML 阅读页：走 `html-page` + 内嵌 `references/frontend-design`，并判断单页/扁平多页/层级多页）、`pretty-view-ppt`（将已有内容做成 HTML 演示文稿：html-ppt 为默认，点名 reveal.js 时走 html-slides）、`lark-cli`（飞书 CLI 薄路由，按需 `lark-cli skills read`）、`dotf-ui-design`（UI Engineering 薄路由：frontend-design 走全局 defaults，其余 4 条能力 skill 为内部引用）、`task-design`（复杂任务可选设计环节）、`taskflow`（driver change 编排一批子 change，零脚本）。OpenSpec 阶段 skill 由 `dotf agents -c` 默认装到全部 skill layout（`openspec init --tools agents`），不必写入本目录或各项目 `.cursor/skills`；`taskflow` 在已安装时委托它们。

第三方编目（`agents/skills.yaml` + `agents/skills.lock.yaml`）：`mattpocock/skills` 的 `setup-matt-pocock-skills`、`grill-with-docs`、`grilling`、`to-spec`、`to-tickets`、`implement`、`code-review`、`tdd`、`diagnosing-bugs`、`codebase-design`、`domain-modeling`、`research`、`wayfinder`，以及 `sunzhenkai/ui-templates-skill` 的 `ui-template-author`、`ui-template-apply`、`ui-template-design`。由锁定目录安装到全部 skill layout（`~/.agents/skills`、`${KIRO_HOME:-~/.kiro}/skills`、`~/.claude/skills`），并带上 skill 根下的配套文件（如 `catalog/`、`runtime/`），仍排除 `patches/` 等 authoring 目录。`taste-skill` 的 group 已在编目中注释，故不自动装也不能经 overlay/apply 引用（其审计锁保留）；`dotf skills -i taste-skill` 会按字面透传给 npx 搜索安装。

## Managed ownership 与冲突

`dotf agents -c` 先生成无网络、无 secret lookup、无写盘的 plan；确认后才写 HOME。runtime bundle 由 `${XDG_STATE_HOME:-$HOME/.local/state}/dotf/` 下的版本化 managed manifest 记录 owner、source identity 与 hash。只有上次 owned 且仍匹配 managed hash 的 stale 项会被 prune；未托管同名项或本机改写进入 `conflict`，默认保持原样，不静默覆盖。`patches/`、`evals/`、`experience/`、`evolutions/` 等 authoring 数据不属于默认 runtime bundle。


## TUI manager (`dotf tui`)

`dotf tui` 是模块 / Skill 与状态漂移的**管理页面**，不是 plan-only 皮肤：

- **顶部 tab**：`Tab` / `Shift+Tab`（或 `l` / `h`）切换 Modules / Skills / Status / Conflicts；`1`-`4` 直达；默认落在 Modules 清单
- **单行一项**：每个模块 / Skill 占一行；不再被 install / config / deconfig 等动作稀释
- **状态栏**：始终列出移动快捷键（`j`/`k` 上下、`C-d`/`C-u` 半屏、`gg`/`G` 首末）；光标所在行追加已声明动作的快捷键、动作名与简述（未声明的动作不出现）
- **按键即时触发**：模块行按 `i` install / `c` config / `d` deconfig / `u` uninstall / `D` doctor；Skill 行按 `a` apply / `x` remove；弹出进度窗、留在 TUI 内、完成后按 Enter 继续、状态就地刷新
- **批量**：`space` 勾选多行（`[x]` 高亮）后 `Enter` 在 TUI 内一次性跑；`Ctrl-x` 清空勾选（y/N，默认 N）
- **过滤 / 跳转**：按 `/` 进入过滤；`j`/`k` 上下移动；`Ctrl-d`/`Ctrl-u` 半屏；`g g` 顶、`G` 底；`Esc` 清空过滤
- **危险动作二次确认**：`u` / `d` / `x` 在按下后弹 y/N 确认，默认 `N`
- **状态来源**：`XDG_STATE_HOME/dotf/modules-state.yaml`（模块 install/config 事实）+ managed manifest（漂移）+ `agents/env/overlay.*.yaml`（Skill Desired Set）。TUI 只读不写
- **全局 AGENTS.md 漂移**：Status / Conflicts 面板复用 instruction planner 聚合 `agents:instructions:` 漂移，与 doctor 的 `instructions` 段同源
- **退出回显**：TUI 退出时在 stdout 打印本会话改动清单（或 "本会话无改动"）

详细键位速查与状态优先级见 `openspec/changes/dotf-tui-manager/`。

约束：
- 仅在 TTY 下打开；非 TTY 立即失败并指向 CLI
- 缺 Textual 时失败并指向 `mise exec -- pip install textual`
- TUI 不直接写 HOME / overlay / state / manifest；所有改动通过 `bin/dotf` 子命令
