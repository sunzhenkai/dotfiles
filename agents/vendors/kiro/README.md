# Kiro CLI

[Kiro](https://kiro.dev/docs/cli/) Agent CLI 的安装与配置。主目录：

```text
~/.kiro/
├── settings/
│   ├── mcp.json          ← 全局 MCP（托管写入处）
│   └── cli.json          ← CLI 设置
├── skills/               ← 用户级 skills（亦作 /skill-name slash）
├── prompts/              ← 用户级无参 prompts（@name / /prompts）
├── agents/               ← 自定义 agents
└── steering/             ← steering 上下文
```

可用环境变量 `KIRO_HOME` 重定向整个全局目录。

## 安装

```shell
dotf kiro -i
# 或随 agents 工具包
dotf agents -i
```

官方：`curl -fsSL https://cli.kiro.dev/install | bash`（bin: `kiro-cli`，通常落到 `~/.local/bin`）。

首次使用需 `kiro-cli login` 完成鉴权。

## 配置

```shell
dotf kiro -c
```

确保 `~/.kiro/{skills,prompts,settings}` 就绪。共享 skills / prompts / MCP：

```shell
dotf agents -c --tool kiro
# 或
scripts/agents/sync.sh kiro
```

## 官方资源布局

| 资源 | 用户级位置 | 项目级位置 |
|------|------------|------------|
| Skills | `~/.kiro/skills/` | `.kiro/skills/` |
| Prompts | `~/.kiro/prompts/` | `.kiro/prompts/` |
| MCP | `~/.kiro/settings/mcp.json` | `.kiro/settings/mcp.json` |
| Agents | `~/.kiro/agents/` | `.kiro/agents/` |
| Steering | `~/.kiro/steering/` | `.kiro/steering/` |

加载优先级（MCP）：Agent Config > Workspace > Global。

## 本仓库 sync 写入范围

| 目标 | 写入位置 | 说明 |
|------|----------|------|
| Skills | `~/.kiro/skills/` | 用户级；workspace `.kiro/` 不写 |
| Commands | `~/.kiro/skills/<command>/SKILL.md` | 映射为可接收 `$ARGUMENTS` 的 slash skill；同名共享 skill 直接复用 |
| MCP | merge → `~/.kiro/settings/mcp.json` 的 `mcpServers` | 保留非托管 server |

`agents/vendors/kiro/mcp.json` 是 **agents/env 生成物**。请改 `agents/env/mcp/` 后运行：

```shell
dotf agents -c
scripts/agents/sync.sh kiro
```

默认 profile 为 `browser`（智谱 web MCP + Playwright）。
只要搜索不要浏览器时用 `--profile research`。

密钥使用占位符 `${ZHIPU_API_KEY}`，在环境变量中设置真实值。详见 `agents/env/README.md`。
