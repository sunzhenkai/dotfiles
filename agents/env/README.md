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
| `research` | coding 检查 + 智谱 web MCP | low |
| `browser`（默认） | research + Playwright 自动化 | high |
| `full` | 完整能力（含 browser） | high |

`dotf agents -c` 默认使用 `browser` profile，会写入 Playwright MCP。若只要 web 搜索、不要浏览器自动化，用 `--profile research` 或在 `local.yaml` 设 `profile: research`。

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
- 默认 **隔离** user-data-dir：`/tmp/agent-env/browser/profile`
- 截图 / trace 建议目录：`/tmp/agent-env/browser/artifacts`（**不要提交**）
- Chrome DevTools / 真实主 profile：仅 local override 显式 opt-in，doctor 会标 high risk

启用流程：

```shell
scripts/agents/sync.sh cursor --env-only --profile browser
python3 scripts/agents/doctor.py --profile browser --tool cursor --verbose
```

同步后重载或重启对应 agent 客户端，让新的 MCP 配置生效。默认 `browser` / `full` 会生成 `playwright`；显式 `--profile research` 或 `coding` 则不启用浏览器自动化。

Smoke test：

1. 在启用 browser profile 的 agent 中打开 `https://example.com`。
2. 读取页面 snapshot，确认能看到 Example Domain。
3. 如需视觉检查，再请求 screenshot；指定文件名时使用 artifact 目录下的绝对路径，例如 `/tmp/agent-env/browser/artifacts/example.png`。
4. 若 provider 启动失败，先运行 `npx playwright install chromium`；Linux 缺系统依赖时再按 Playwright 提示运行 `npx playwright install-deps`。

截图、trace、downloads、浏览器 profile 都可能包含私有信息；不要提交到仓库，也不要把包含登录态的真实 profile 作为默认配置。headed/xvfb、`browser_executable`、CDP endpoint、真实 profile 只能通过 `agents/env/local.yaml`、`agents/env/local/*.yaml` 或环境变量显式 opt-in。

## 安全

- 仓库只存变量**名**与占位符（Cursor/Claude: `${ZHIPU_API_KEY}`；OpenCode: `{env:ZHIPU_API_KEY}`；Kimi: `bearerTokenEnvVar`）
- 真实密钥只放环境变量或系统 keychain
- 本机路径只放 `local.yaml`
- doctor 会扫描明显 secret / 内网 URL，且**永不打印** secret 值
- Kimi Code **不会**展开 `headers` 里的 `${ENV}`；若写成字面量会收到智谱 `{"code":401,...}`（非 JSON-RPC），表现为 MCP initialize 校验失败
- MiniMax：`MINIMAX_API_KEY`（本仓库 Codex 打**国内** `api.minimaxi.com`）与 Pi 海外 provider `minimax`（`api.minimax.io`）**不是一回事**；国内 key 用 Pi 须走 `minimax-cn` / `MINIMAX_CN_API_KEY`。专题：`repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`
- Kimi（Pi）：`KIMI_API_KEY` → 内置 provider `kimi-coding`；`dotf pi -c` 会写入 `auth.json` 的 `$KIMI_API_KEY` 引用

## 与工具配置的关系

Claude / Cursor / OpenCode / Kimi / ZCode / Qoder / CodeBuddy 的 MCP 片段由本目录生成或合并：

```shell
scripts/agents/sync.sh claude|cursor|opencode|kimi-code|zcode|qoder|codebuddy-code|pi
```

Codex / Pi 当前无稳定 MCP 入口 → sync/doctor 记为 `skip`（skills/prompts 仍走 `agents/`）。
`codebuddy-code` 为 opt-in 安装模块，但仍参与 MCP sync。

仓库内 `agents/vendors/claude/.mcp.json`、`agents/vendors/cursor/mcp.json`、`agents/vendors/opencode/opencode.json`、`agents/vendors/kimi-code/mcp.json`、`agents/vendors/zcode/mcp.json`（`mcp.servers`）、`agents/vendors/qoder/settings.json`（仅 `mcpServers`）、`agents/vendors/codebuddy-code/.mcp.json` 的 MCP 段视为**生成物**；请改 `agents/env/mcp/` 后重新 sync，不要手写多源漂移。
