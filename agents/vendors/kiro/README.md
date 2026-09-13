# Kiro CLI

[Kiro](https://kiro.dev/docs/cli/) Agent CLI 的安装与配置。主目录：

```text
~/.kiro/
├── settings/
│   └── cli.json          ← CLI 设置
├── skills/               ← 用户级 skills（亦作 /skill-name slash）
├── prompts/              ← 用户级无参 prompts（@name / /prompts）
├── agents/               ← 自定义 agents
└── steering/             ← steering 上下文
```

可用环境变量 `KIRO_HOME` 重定向整个全局目录。
dotf 托管写入要求 `KIRO_HOME` 位于 HOME 内；指向 HOME 外会在 dry-run/apply 阶段拒绝。

## 安装

```shell
dotf kiro -i
# 或随 agents 工具包
dotf agents -i
```

官方：`curl -fsSL https://cli.kiro.dev/install | bash`（bin: `kiro-cli`，通常落到 `~/.local/bin`）。

首次使用需 `kiro-cli login` 完成鉴权。

## 配置

Kiro 不读取共享 `~/.agents/skills`；`dotf agents -c` 会托管 Kiro skills 镜像，并为 slash skill 追加 `$ARGUMENTS`。`dotf kiro` 模块只负责安装 CLI：

```shell
dotf agents -c
# 或
scripts/modules/agents/sync.sh all
```

## 官方资源布局

| 资源 | 用户级位置 | 项目级位置 |
|------|------------|------------|
| Skills | `~/.kiro/skills/` | `.kiro/skills/` |
| Prompts | `~/.kiro/prompts/` | `.kiro/prompts/` |
| Agents | `~/.kiro/agents/` | `.kiro/agents/` |
| Steering | `~/.kiro/steering/` | `.kiro/steering/` |

## 本仓库 sync 写入范围

| 目标 | 写入位置 | 说明 |
|------|----------|------|
| Skills | `~/.kiro/skills/` | 用户级；workspace `.kiro/` 不写 |
| Commands | `~/.kiro/skills/<skill-id>/SKILL.md` | 共享 skill 映射为可接收 `$ARGUMENTS` 的 slash skill |

Kiro skills 由 managed manifest 独立跟踪（owner 前缀 `agents:kiro-skill:`）。未托管或本机修改的同名文件会保持原样并报告 conflict，不会静默覆盖。
