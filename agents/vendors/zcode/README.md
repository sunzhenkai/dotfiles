# ZCode

[ZCode](https://zcode.z.ai/) Agent 的安装与配置。主目录：

```text
~/.zcode/
├── cli/                      ← CLI 客户端数据
│   ├── agents/
│   ├── artifacts/
│   ├── db/  log/  exec/
│   ├── plugins/              ← 插件、marketplace、MCP 数据
│   ├── config.json           ← 含 mcp.servers（托管 MCP 写入处）
│   └── rollout/
├── server/                   ← 内置 Node 运行时 + zcode-server.cjs
├── v2/                       ← 任务索引
├── skills/                   ← 用户级 skills
└── commands/                 ← 用户级 commands
```

## 安装

```shell
dotf zcode -i
# 或随 agents 工具包
dotf agents -i
```

安装 `zcode-app-cli`（bin: `zcode`）。桌面端可另行从官网下载；数据目录同为 `~/.zcode`。

## 配置

```shell
dotf zcode -c
```

确保 `~/.zcode/{skills,commands,cli}` 就绪。共享 skills / commands / MCP：

```shell
dotf agents -c --tool zcode
# 或
scripts/agents/sync.sh zcode
```

## ZCode 资源布局（官方）

| 资源 | 用户级位置 | 项目级位置 | 冲突规则 |
|------|------------|------------|----------|
| Skills | `~/.zcode/skills/`、`~/.agents/skills/` | `<repo>/.zcode/skills/`、`<repo>/.agents/skills/` | 同名第一个赢，user 优先 |
| Commands | `~/.zcode/commands/`、`~/.agents/commands/` | `<repo>/.zcode/commands/`、`<repo>/.agents/commands/` | 同名第一个赢，user 优先 |
| MCP | `~/.zcode/cli/config.json` → `mcp.servers` | `<repo>/.zcode/config.json` → `mcp.servers` | user 覆盖 workspace；各层自动连接 |
| Hooks | `~/.zcode/cli/config.json` → `hooks`（需 `hooks.enabled:true`） | `<repo>/.zcode/config.json` → `hooks` | 配置式需显式 enable；插件 hook 自动追加 |
| Plugins | marketplace 安装，开关存于 `~/.zcode/cli/config.json` → `plugins` | — | 插件可贡献 skill/command/hook/MCP/agent |

## 本仓库 sync 写入范围

| 目标 | 写入位置 | 说明 |
|------|----------|------|
| Skills | `~/.zcode/skills/` | 用户级主路径（不写 `~/.agents/` / 项目级） |
| Commands | `~/.zcode/commands/` | 同上 |
| MCP | merge → `~/.zcode/cli/config.json` 的 `mcp.servers` | 保留非托管 server 与其它本机字段 |
| Hooks / Plugins | — | 不由 agents sync 管理 |

`agents/vendors/zcode/mcp.json` 为 **agents/env 生成物**（`{"mcp":{"servers":...}}` 片段，只含占位符）；请改 `agents/env/mcp/` 后重新 sync。

ZCode **不展开** `${ZHIPU_API_KEY}`。同步本机 MCP 时会把密钥写入 `~/.zcode/cli/config.json`，否则 HTTP MCP 会鉴权失败。仓库模板不会写入真实密钥。
