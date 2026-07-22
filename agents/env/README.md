# agents/env

Agent **运行环境**真相源（MCP、依赖、env schema、browser、安全策略）。

已归入统一 agent 域 `agents/`：`skills/` / `commands/` / `vendors/` / `env/`。

## 边界

| 子目录 | 职责 |
|--------|------|
| `agents/skills/`、`agents/commands/` | 提示词与工作流 |
| `agents/vendors/` | 各工具适配模板（含 MCP 生成物） |
| `agents/env/` | MCP、CLI/runtime、env 检查、browser、安全边界 |

不要把 skill/command 写进本目录；也不要把 API Key、cookie、浏览器 profile 提交到仓库。

## 统一入口

```shell
dotf agents -c
dotf agents -d
dotf agents -cd
scripts/agents/sync.sh all
scripts/agents/sync.sh --env-only
python3 scripts/agents/doctor.py
```

## 布局

```text
agents/env/
  README.md
  manifest.yaml           # 工具范围、默认 profile、模块启用
  env.schema.yaml         # 变量名 / 用途 / 敏感等级（无真实密钥）
  tools.yaml              # CLI/runtime 检查与安装提示
  security.yaml           # 风险等级与敏感扫描规则
  browser.yaml            # Playwright 默认 + Chrome DevTools 可选
  local.yaml.example      # 本机覆盖示例
  local.yaml              # gitignored 本机覆盖
  mcp/
    servers.yaml          # MCP server 真相源
    profiles/             # coding | research | browser | full
```

## Profiles

| Profile | 内容 | 风险 |
|---------|------|------|
| `coding` | 本地 CLI/runtime 检查 | low |
| `research`（默认） | coding 检查 + 智谱 web MCP | low |
| `browser` | research + Playwright 自动化 | high |
| `full` | 完整能力（含 browser） | high |

浏览器自动化**不会**随默认 `research` 启用。

## 快速使用

```shell
dotf agents -c
scripts/agents/sync.sh cursor --profile research
scripts/agents/sync.sh all --dry-run
scripts/agents/sync.sh all --env-only --profile browser
python3 scripts/agents/doctor.py
python3 scripts/agents/doctor.py --profile browser --verbose
```

## 本机覆盖

```shell
cp agents/env/local.yaml.example agents/env/local.yaml
```

可覆盖：默认 profile、禁用/启用 server、headed 模式、浏览器路径、CDP endpoint。  
`local.yaml` 与 `local/` 已被 gitignore。

## Browser MCP

- 默认 provider：`@playwright/mcp`（`npx -y @playwright/mcp@latest`）
- 默认 **隔离** user-data-dir：`~/.cache/agent-env/browser/profile`
- 截图 / trace 建议目录：`~/.cache/agent-env/browser/artifacts`（**不要提交**）
- Chrome DevTools / 真实主 profile：仅 local override 显式 opt-in，doctor 会标 high risk

## 安全

- 仓库只存变量**名**与占位符（Cursor/Claude: `${ZHIPU_API_KEY}`；OpenCode: `{env:ZHIPU_API_KEY}`；Kimi: `bearerTokenEnvVar`）
- 真实密钥只放环境变量或系统 keychain
- 本机路径只放 `local.yaml`
- doctor 会扫描明显 secret / 内网 URL，且**永不打印** secret 值
- Kimi Code **不会**展开 `headers` 里的 `${ENV}`；若写成字面量会收到智谱 `{"code":401,...}`（非 JSON-RPC），表现为 MCP initialize 校验失败
- MiniMax：`MINIMAX_API_KEY`（本仓库 Codex 打**国内** `api.minimaxi.com`）与 Pi 海外 provider `minimax`（`api.minimax.io`）**不是一回事**；国内 key 用 Pi 须走 `minimax-cn` / `MINIMAX_CN_API_KEY`。专题：`repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`
- Kimi（Pi）：`KIMI_API_KEY` → 内置 provider `kimi-coding`；`dotf pi -c` 会写入 `auth.json` 的 `$KIMI_API_KEY` 引用

## 与工具配置的关系

Claude / Cursor / OpenCode / Kimi 的 MCP 片段由本目录生成或合并：

```shell
scripts/agents/sync.sh claude|cursor|opencode|kimi-code|pi
```

Codex / Pi 当前无稳定 MCP 入口 → sync/doctor 记为 `skip`（skills/prompts 仍走 `agents/`）。

仓库内 `agents/vendors/claude/.mcp.json`、`agents/vendors/cursor/mcp.json`、`agents/vendors/opencode/opencode.json`、`agents/vendors/kimi-code/mcp.json` 的 MCP 段视为**生成物**；请改 `agents/env/mcp/` 后重新 sync，不要手写多源漂移。
