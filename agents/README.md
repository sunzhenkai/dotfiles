# Shared agent skills & commands

跨 Claude Code / Cursor / Kiro / OpenCode / Codex / Kimi Code / Pi / ZCode / Qoder / CodeBuddy 的 **skills / commands 唯一真相源**。

## 统一入口（推荐）

**边界**：`agents` 负责聚合安装计划与共享 skills/commands/MCP 同步；单工具模块只处理本工具 CLI/vendor 配置，**不会**隐式全量 sync。

```shell
dotf agents -i                 # 计划展开为各 agent CLI 的独立 install 动作
dotf claude -i                 # 仅安装 Claude CLI
dotf cursor -c                 # 仅应用 Cursor vendor 配置（不 sync skills/MCP）
dotf agents -c                 # 聚合同步 skills + MCP（全部工具）
dotf agents -c --tool cursor   # 显式过滤：只同步 Cursor 适用目标
dotf agents -d                 # L0 诊断
dotf agents -d --deep          # L0 + agents L1 深度诊断
dotf agents -d --deep --json   # 深度诊断 JSON（凭据脱敏）
dotf agents -cd                # 先同步再诊断
scripts/agents/sync.sh all
scripts/agents/sync.sh cursor  # 等价过滤入口
python3 scripts/agents/doctor.py
```

## 布局

```text
agents/
  skills/<skill-id>/SKILL.md       # skill 源（frontmatter 渲染后分发）
  skills/<skill-id>/references/    # 可选：随 skill 原样分发（不做渲染/替换，字节一致）
  skills/<skill-id>/scripts/       # 可选：随 skill 原样分发（helper CLI / 审计脚本）
  commands/<command-id>.md         # command 源
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

**Command** 至少包含：

```yaml
---
id: my-command
title: "My Command"   # Claude 显示名等
description: ...
category: Workflow    # 可选
tags: [a, b]          # 可选
---
```

共享 command 源 **不要** 写 OpenCode-only 字段（如 `agent:`）；需要时由适配层注入。

## 脚本与模型的分工（写 skill 脚本前必读）

skill 自带脚本（`scripts/`）只做**确定性**的事：读写结构化文件、算 ID、跑 git、校验格式、汇报事实。**理解自然语言、判断意图与性质是模型的职责**，不要外包给正则。

- **禁止**让脚本从用户消息 / 自由文本里「挖」需求、意图或语义分类。模型先归纳，再把结论**作为参数**传给脚本（如 `--title` / `--slug`）。
- **禁止**要求 Agent 把渲染后的消息逐字转存给脚本解析。模型无法可靠复现自己的输入，漏抄是静默的，脚本无从校验，最后会把转录失误变成对用户的错误追问。
- **禁止**用关键词表决定门禁强度（「这条待办算不算测试项」这类）。脚本列事实与原文，模型说明判断，**用户拍板**。
- 需要按宿主（Cursor / Claude / Kiro …）渲染格式加解析分支时，说明设计错了：换成模型理解 + 参数传入，而不是再加一条围栏规则。
- 正例：`taskctl resolve` 把确定性来源（唯一编号、cwd、分支名）直接采用，启发式来源一律 `needs_confirm` 交用户；`audit-skill.sh` 只报命中行，由 Agent 复核、用户豁免。

## 语言

skills / commands 面向用户的说明与输出默认 **简体中文**。
id、slash 命令、路径、代码、状态值、CLI flag 与既成术语（如 OpenSpec、Gate、Blocker）保持原文，不要逐词硬翻。
`en-chat` 除外（陪练回复用英语）。`references/` 原样分发，不要求翻译。

## 占位符

正文里需要 slash 命令时，写：

```text
{{slash:opsx-apply}}
```

同步时按工具替换：

| 工具 | `opsx-apply` 示例 |
|------|-------------------|
| claude | `/opsx:apply` |
| cursor / kiro / opencode / codex / kimi-code / pi / zcode / qoder / codebuddy-code | `/opsx-apply` |

## 排除某一工具

在条目旁放 `exclude` 文件（每行一个工具名）：

```text
agents/skills/my-skill/exclude
agents/commands/my-command.exclude
```

内容示例：

```text
codex
```

未声明 `exclude` 时，默认对全部 `TOOLS`（含 opt-in 的 `codebuddy-code`）启用。

## 同步

```bash
# 同步全部工具
scripts/agents/sync.sh all

# 或单个
scripts/agents/sync.sh claude
scripts/agents/sync.sh cursor
scripts/agents/sync.sh kiro
scripts/agents/sync.sh opencode
scripts/agents/sync.sh codex
scripts/agents/sync.sh kimi-code
scripts/agents/sync.sh pi
scripts/agents/sync.sh zcode
scripts/agents/sync.sh qoder
scripts/agents/sync.sh codebuddy-code

# 也可用配置入口
scripts/config.sh agents
```

共享 sync：`dotf agents -c [--tool <name>]`。单工具 `dotf <tool> -c` 只应用 vendor 配置，不隐式全量 sync。
`codebuddy-code` 为 **opt-in**（`enabled: false`）：不随 `dotf agents -i` / `--all` 安装，但参与 sync/doctor。
`minimax`（MiniMax CLI，bin: `mmx`）随 `dotf agents -i` 安装并参与 doctor；无 skills/commands/MCP 布局，**不参与 sync**（env_sync 为 skip stub）。

## 安装目标

| 工具 | Skills | Commands |
|------|--------|----------|
| claude | `~/.claude/skills/` + 仓库 `.claude/skills/`（生成） | `~/.claude/commands/` + `.claude/commands/` |
| cursor | `~/.cursor/skills/` + `.cursor/skills/` | `~/.cursor/commands/` + `.cursor/commands/` |
| kiro | `~/.kiro/skills/` | `~/.kiro/skills/<command>/SKILL.md`（slash 参数通过 `$ARGUMENTS` 注入；同名 skill 直接复用） |
| opencode | `~/.config/opencode/skills/` | `~/.config/opencode/commands/` |
| codex | `~/.codex/skills/` | `~/.codex/prompts/`（降级映射） |
| kimi-code | `~/.kimi-code/skills/` | skip（无稳定 commands 布局） |
| pi | `~/.pi/agent/skills/` | `~/.pi/agent/prompts/`（prompt templates） |
| zcode | `~/.zcode/skills/` | `~/.zcode/commands/`（MCP：`~/.zcode/cli/config.json` → `mcp.servers`） |
| qoder | `~/.qoder-cn/skills/` | `~/.qoder-cn/commands/` |
| codebuddy-code | `~/.codebuddy/skills/` | `~/.codebuddy/commands/` |
| minimax | 不同步（mmx 无此布局） | 不同步（mmx 无此布局；MCP 亦 skip） |

**不要手改** `.claude/`、`.cursor/`、`~/.config/opencode/skills|commands` 里由本系统生成的文件；请改 `agents/skills|commands` 后重新 sync。

## 示例条目

仓库自带：`browser`、`commit-push`、`en-chat`、`repo-manager`、`role-based-reviewer`、`service-manager`、`skills-store`、`skill-evolver`（skill + command；从多次真实执行进化已有 Skill：候选 patch → 验证 → 晋升/拒绝，不直接改生产稿，也不在每次任务后自动改）、`skill-upgrader`（skill + command；把已有 `SKILL.md` 一次性升级为带 `examples/` `evals/` `experience/` 的自进化结构，不伪造历史、不按单次失败改正文；真正改生产稿仍走 `skill-evolver`）、`dotf-ui-design`（skill + command）、`pretty-view`（文档/知识/报告/code review/方案的 HTML 或 Markdown 展示门卫：普通 HTML 阅读页走 `html-page` + `frontend-design`，并判断单页/扁平多页/层级多页；baoyu 与 html-ppt/html-slides 只认显式口令）、`lark-cli`（飞书 CLI 薄路由，按需 `lark-cli skills read`）、`task-workflow`（skill + `task-new`/`task-explore`/`task-design`/`task-propose`/`task-apply`/`task-archive` commands）、`task-design`（复杂任务可选设计环节）、`taskflow`（skill + `taskflow-new` command；driver change 编排一批子 change，零脚本，与 `task-workflow` 并存但互斥）。OpenSpec 阶段 skill 请用各工具 CLI 初始化，不必放进本目录；`task-workflow` 在已安装时委托它们。
