# Shared agent skills

跨 Cursor / Kiro / OpenCode / Codex / Kimi Code / Pi / ZCode / DeepSeek Harness（dsh）等工具的 **skills 唯一真相源**。

## 统一入口（推荐）

**边界**：`agents` 负责聚合安装计划与共享 skills/MCP 同步；Cursor、Kiro、ZCode 的 MCP 只由 agents sync 管理，单工具模块只安装 CLI。

```shell
dotf agents -i                 # 计划展开为各 agent CLI 的独立 install 动作
dotf cursor -i                 # 仅安装 Cursor CLI
dotf agents -c                 # 聚合同步 skills（~/.agents/skills）+ 全局 AGENTS.md + MCP（全部工具）
dotf agents -c --tool cursor   # 显式过滤：只同步 Cursor 的 MCP（skills 与 tool 无关，始终全量）
dotf skills -i <skill-name>    # 用 npx skills 按需安装；短名先经 skills-map.yaml 映射；默认交互式，-g 全局 / --project 项目 / -y 跳过询问
dotf skills -r <skill-name>    # 移除已安装 skill（省略名称进入 npx skills 交互式移除；短名同走映射）
dotf agents skill apply <id>   # 写入本机 overlay Desired Set 并 sync
dotf agents skill remove <id>  # 停用并 prune owned 且未漂的目标（不改仓库）
dotf agents mcp apply <id> --tool cursor
dotf agents mcp remove <id> --all-tools
dotf agents -d                 # L0 诊断
dotf agents -d --deep          # L0 + agents L1 深度诊断
dotf agents -d --deep --json   # 深度诊断 JSON（凭据脱敏）
dotf agents -cd                # 先同步再诊断
scripts/agents/sync.sh all
scripts/agents/sync.sh cursor  # 等价过滤入口（仅影响 MCP/env 部分）
python3 scripts/agents/doctor.py
```

## 布局

```text
agents/
  skills/<skill-id>/SKILL.md       # 一手 skill 源（frontmatter 渲染后分发）
  skills/<skill-id>/references/    # 可选：随 skill 原样分发（不做渲染/替换，字节一致）
  skills/<skill-id>/scripts/       # 可选：随 skill 原样分发（helper CLI / 审计脚本）
  instructions/AGENTS.md           # 全局 agent 指令（用户级，跨项目）
  instructions/install.yaml        # 安装目标（~/.agents、Codex、Cursor rules）
  skills-defaults.yaml             # 第三方默认 skill（锁定后装到 ~/.agents/skills）
  vendors/<tool>/                  # 工具专属 settings / 人格 / 生成物
  env/                             # MCP / profiles / browser / security 真相源
  README.md
```

工具专属 settings、OpenCode 人格等放在 `agents/vendors/<tool>/`。  
MCP / env / browser 真相源在 `agents/env/`，由单一脚本包 `scripts/agents/` 编排，不要手写多源漂移。

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

同步时统一渲染为 `/opsx-apply`（共享目标是 `~/.agents/skills`；Kiro CLI 例外，见下文）。

## 同步

skills 默认同步到共享目标：`~/.agents/skills/<id>/`（含 `references/`、`scripts/` sidecar，原样字节分发）。各 agent 工具从该目录读取共享 skill；本系统不再向各工具私有目录写镜像。**Kiro CLI 是当前唯一例外**：它不读取 `~/.agents/skills`，因此同一入口会额外托管一份 `${KIRO_HOME:-~/.kiro}/skills/<id>/`，并在 `SKILL.md` 末尾补上 Kiro slash 参数占位 `$ARGUMENTS`。`KIRO_HOME` 必须指向 HOME 内的真实目录，避免越过 dotf 的 HOME 写入边界。

同一入口还会安装全局 `AGENTS.md`（跨项目默认指令，不含 skill 目录）：`~/.agents/AGENTS.md`、`~/.codex/AGENTS.md`，以及 Cursor 用户级 `~/.cursor/rules/00-dotf-global.mdc`。源在 `agents/instructions/`。**不要手改**这些安装产物。漂移在 doctor 的 `instructions` 段与 TUI 的 Status / Conflicts 面板可见。

本机 Skill Desired Set = 一手 catalog ∪ `skills-defaults.yaml` 默认选中项 ∪ overlay `enabled_skills` − `disabled_skills`。未锁定第三方与 OpenSpec 生成的 `openspec-*` 不能进入 Desired Set。apply / remove 只改 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/`，不改仓库 catalog / lock。

一手 skill 来自 `agents/skills/`。第三方默认 skill 见 `agents/skills-defaults.yaml`，由同一入口通过锁定目录安装到同一个 `~/.agents/skills`。OpenSpec 阶段 skill **不**放进 `agents/skills/`：同一入口调用本机 `openspec init --tools agents`，把 CLI 生成的 `openspec-*` 装到全局 `~/.agents/skills`（Kiro 例外镜像照旧）。缺少 openspec CLI 时只警告，不阻断一手 skill 同步；技能集合跟随用户的 OpenSpec profile / workflows。

```bash
# 同步 skills（tool 无关，一次性）+ 全部工具的 MCP/env
scripts/agents/sync.sh all

# tool 参数只过滤 MCP/env 部分；skills（含 Kiro 例外镜像）始终全量同步
scripts/agents/sync.sh cursor

# 只同步 skills
scripts/agents/sync.sh --skills-only

# 也可用配置入口
scripts/config.sh agents
```

共享 sync：`dotf agents -c [--tool <name>]`（`--tool` 只过滤 MCP/env）。单工具 `dotf <tool> -c` 只应用 vendor 配置，不隐式全量 sync。
`dsh`（DeepSeek Harness CLI，bin: `dsh`）：MCP client 配置在 profile 内，不参与 agents/env 聚合（env_sync 为 skip stub）。安装走 `dotf dsh -i`。

**不要手改** `~/.agents/skills/` 或 `${KIRO_HOME:-~/.kiro}/skills/` 里由本系统生成的文件；一手 skill 请改 `agents/skills` 后重新 sync，默认第三方 skill 请改 `agents/skills-defaults.yaml`，OpenSpec 阶段 skill 请升级 CLI 后重新 `dotf agents -c`。

## 示例条目

仓库自带：`commit-push`、`en-chat`、`repo-manager`、`role-based-reviewer`、`service-manager`、`skills-store`、`skill-evolver`（从多次真实执行进化已有 Skill：候选 patch → 验证 → 晋升/拒绝，不直接改生产稿，也不在每次任务后自动改）、`skill-upgrader`（把已有 `SKILL.md` 一次性升级为带 `examples/` `evals/` `experience/` 的自进化结构，不伪造历史、不按单次失败改正文；真正改生产稿仍走 `skill-evolver`）、`pretty-view-html`（将已有内容做成 HTML 阅读页：走 `html-page` + 内嵌 `references/frontend-design`，并判断单页/扁平多页/层级多页）、`pretty-view-ppt`（将已有内容做成 HTML 演示文稿：html-ppt 为默认，点名 reveal.js 时走 html-slides）、`lark-cli`（飞书 CLI 薄路由，按需 `lark-cli skills read`）、`dotf-ui-design`（UI Engineering 薄路由：frontend-design 走全局 defaults，其余 4 条能力 skill 为内部引用）、`task-design`（复杂任务可选设计环节）、`task-grill`（taskflow 链路上 explore 与 propose 之间的可选收敛）、`taskflow`（driver change 编排一批子 change，零脚本）。OpenSpec 阶段 skill 由 `dotf agents -c` 默认装到全局 `~/.agents/skills`（`openspec init --tools agents`），不必写入本目录或各项目 `.cursor/skills`；`taskflow` 在已安装时委托它们。

第三方默认（`agents/skills-defaults.yaml` + `agents/skills-defaults.lock.yaml`）：`mattpocock/skills` 的 `setup-matt-pocock-skills`、`grill-with-docs`、`to-spec`、`to-tickets`、`implement`、`code-review`、`tdd`、`diagnosing-bugs`、`codebase-design`、`domain-modeling`、`research`、`wayfinder`，以及 `sunzhenkai/ui-templates-skill` 的 `ui-template-author` 与 `ui-template-apply`。由锁定目录安装到 `~/.agents/skills`，并带上 skill 根下的配套文件（如 `catalog/`、`runtime/`），仍排除 `patches/` 等 authoring 目录。`Leonxlnx/taste-skill` 的 `taste-skill` 已从默认移除，但仍在审计锁中：可通过本机 overlay 显式启用，或用 `dotf skills -i taste-skill` 按需安装（短名映射见 `agents/skills-map.yaml`）。

## Managed ownership 与冲突

`dotf agents -c` 先生成无网络、无 secret lookup、无写盘的 plan；确认后才写 HOME。runtime bundle 和 MCP server id 由 `${XDG_STATE_HOME:-$HOME/.local/state}/dotf/` 下的版本化 managed manifest 记录 owner、source identity 与 hash。只有上次 owned 且仍匹配 managed hash 的 stale 项会被 prune；未托管同名项或本机改写进入 `conflict`，默认保持原样，不静默覆盖。`patches/`、`evals/`、`experience/`、`evolutions/` 等 authoring 数据不属于默认 runtime bundle。

多目标 MCP apply 使用 transaction journal，提交失败时逆序 rollback。`failed-rollback` 表示回滚也失败：保留 journal/备份，按其中的受限路径与 hash 人工恢复后再运行 dry-run；不要删除 journal 或把运行目录重新软链到仓库。

## 仓库模板维护

普通 sync 永不更新 `agents/vendors/*` 的 committed MCP 模板。修改 `agents/env/` 安全真相源后，维护者必须显式运行：

```shell
python3 scripts/agents/generate_templates.py
python3 scripts/agents/generate_templates.py --check
git diff --exit-code -- agents/vendors/cursor/mcp.json agents/vendors/kiro/mcp.json \
  agents/vendors/opencode/opencode.json agents/vendors/kimi-code/mcp.json agents/vendors/zcode/mcp.json
```

生成器禁用本机 overlay，不解析 secret 值，只使用 committed safe sources；生成 diff 必须审查并提交。

## TUI manager (`dotf tui`)

`dotf tui` 是模块 / Skill / MCP 与状态漂移的**管理页面**，不是 plan-only 皮肤：

- **顶部 tab**：`Tab` / `Shift+Tab`（或 `l` / `h`）切换 Modules / Skills / MCP / Status / Conflicts；`1`-`5` 直达；默认落在 Modules 清单
- **单行一项**：每个模块 / Skill / MCP 占一行；不再被 install / config / deconfig 等动作稀释
- **状态栏**：始终列出移动快捷键（`j`/`k` 上下、`C-d`/`C-u` 半屏、`gg`/`G` 首末）；光标所在行追加已声明动作的快捷键、动作名与简述（未声明的动作不出现）
- **按键即时触发**：模块行按 `i` install / `c` config / `d` deconfig / `u` uninstall / `D` doctor；Skill / MCP 行按 `a` apply / `x` remove；弹出进度窗、留在 TUI 内、完成后按 Enter 继续、状态就地刷新
- **批量**：`space` 勾选多行（`[x]` 高亮）后 `Enter` 在 TUI 内一次性跑；`Ctrl-x` 清空勾选（y/N，默认 N）
- **过滤 / 跳转**：按 `/` 进入过滤；`j`/`k` 上下移动；`Ctrl-d`/`Ctrl-u` 半屏；`g g` 顶、`G` 底；`Esc` 清空过滤
- **危险动作二次确认**：`u` / `d` / `x` 在按下后弹 y/N 确认，默认 `N`
- **状态来源**：`XDG_STATE_HOME/dotf/modules-state.yaml`（模块 install/config 事实）+ managed manifest（漂移）+ `agents/env/overlay.*.yaml`（Skill / MCP Desired Set）。TUI 只读不写
- **全局 AGENTS.md 漂移**：Status / Conflicts 面板复用 instruction planner 聚合 `agents:instructions:` 漂移，与 doctor 的 `instructions` 段同源
- **退出回显**：TUI 退出时在 stdout 打印本会话改动清单（或 "本会话无改动"）

详细键位速查与状态优先级见 `openspec/changes/dotf-tui-manager/`。

约束：
- 仅在 TTY 下打开；非 TTY 立即失败并指向 CLI
- 缺 Textual 时失败并指向 `mise exec -- pip install textual`
- TUI 不直接写 HOME / overlay / state / manifest；所有改动通过 `bin/dotf` 子命令
