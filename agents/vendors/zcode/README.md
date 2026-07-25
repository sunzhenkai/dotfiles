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

| 目标 | 路径 |
|------|------|
| Skills | `~/.zcode/skills/` |
| Commands | `~/.zcode/commands/` |
| MCP | merge `mcp.servers` → `~/.zcode/cli/config.json` |

`agents/vendors/zcode/mcp.json` 为 **agents/env 生成物**（`{"mcp":{"servers":...}}` 片段）；请改 `agents/env/mcp/` 后重新 sync。已有 `config.json` 中非托管字段与非托管 MCP 会保留。
