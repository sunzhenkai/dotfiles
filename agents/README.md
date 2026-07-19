# Shared agent skills & commands

跨 Claude Code / Cursor / OpenCode / Codex / Kimi Code 的 **skills / commands 唯一真相源**。

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
  skills/<skill-id>/SKILL.md   # skill 源
  commands/<command-id>.md     # command 源
  vendors/<tool>/              # 工具专属 settings / 人格 / 生成物
  env/                         # MCP / profiles / browser / security 真相源
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

## 占位符

正文里需要 slash 命令时，写：

```text
{{slash:opsx-apply}}
```

同步时按工具替换：

| 工具 | `opsx-apply` 示例 |
|------|-------------------|
| claude | `/opsx:apply` |
| cursor / opencode / codex / kimi-code | `/opsx-apply` |

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

未声明 `exclude` 时，默认对 `claude`、`cursor`、`opencode`、`codex`、`kimi-code` 全部启用。

## 同步

```bash
# 同步全部工具
scripts/agents/sync.sh all

# 或单个
scripts/agents/sync.sh claude
scripts/agents/sync.sh cursor
scripts/agents/sync.sh opencode
scripts/agents/sync.sh codex
scripts/agents/sync.sh kimi-code

# 也可用配置入口
scripts/config.sh agents
```

`dotf claude -c|cursor|opencode|codex|kimi-code` 时也会自动同步对应工具。

## 安装目标

| 工具 | Skills | Commands |
|------|--------|----------|
| claude | `~/.claude/skills/` + 仓库 `.claude/skills/`（生成） | `~/.claude/commands/` + `.claude/commands/` |
| cursor | `~/.cursor/skills/` + `.cursor/skills/` | `~/.cursor/commands/` + `.cursor/commands/` |
| opencode | `agents/vendors/opencode/skills/`（随 `~/.config/opencode` symlink） | `agents/vendors/opencode/commands/` |
| codex | `~/.codex/skills/` | `~/.codex/prompts/`（降级映射） |
| kimi-code | `~/.kimi-code/skills/` | skip（无稳定 commands 布局） |

**不要手改** `.claude/`、`.cursor/`、`agents/vendors/opencode/skills|commands` 里由本系统生成的文件；请改 `agents/skills|commands` 后重新 sync。

## 示例条目

仓库自带：`commit-push`、`en-chat`（skill + command）。OpenSpec 等工作流请用各工具 CLI 初始化，不必放进本目录。
