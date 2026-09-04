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
  vendors.yaml            # 单一 vendor capability matrix（CLI/adapter/transport/secret/runtime）
  env.schema.yaml         # 变量名 / 用途 / 敏感等级（无真实密钥）
  tools.yaml              # CLI/runtime 检查与安装提示
  security.yaml           # 风险等级与敏感扫描规则
  browser.yaml            # Playwright 默认 + Chrome DevTools 可选

## Vendor capability matrix

`vendors.yaml` is the single source for sync CLI choices, adapter target/transport support, secret handling, runtime-version reporting, and this table. Catalog validation fails when the table drifts.

<!-- vendor-capabilities:start -->
| Vendor | MCP | Transports | Secret handling | Runtime versions | Target | Notes |
|---|---:|---|---|---:|---|---|
| `cursor` | yes | stdio, streamable-http | `runtime-placeholder` | yes | `~/.cursor/mcp.json` | Cursor MCP JSON; secrets remain runtime placeholders |
| `kiro` | yes | stdio, streamable-http | `runtime-placeholder` | yes | `~/.kiro/settings/mcp.json` | Kiro MCP JSON; secrets remain runtime placeholders |
| `opencode` | yes | stdio, streamable-http | `runtime-placeholder` | yes | `~/.config/opencode/opencode.json` | OpenCode MCP JSON; uses {env:NAME} placeholders |
| `codex` | no | — | `unsupported` | no | — | MCP sync unsupported; shared skills remain supported |
| `kimi-code` | yes | stdio, streamable-http | `environment-reference` | yes | `~/.kimi-code/mcp.json` | Kimi Code uses bearerTokenEnvVar or a runtime shell mapping |
| `pi` | no | — | `unsupported` | no | — | MCP sync unsupported; shared skills remain supported |
| `zcode` | yes | stdio, streamable-http | `literal-at-apply` | yes | `~/.zcode/cli/config.json` | ZCode literals are resolved only after plan approval |
| `dsh` | no | — | `unsupported` | no | — | MCP configuration is profile-local and outside aggregate sync |
<!-- vendor-capabilities:end -->
  overlay.schema.yaml     # 外置 overlay v1 schema（严格 unknown-key/type 校验）
  overlay.example.yaml    # 安全示例；复制到 XDG 配置目录
  mcp/
    servers.yaml          # MCP server 真相源
    profiles/             # coding | research | browser | full
```

## Profiles

| Profile | 内容 | 风险 |
|---------|------|------|
| `coding` | 本地 CLI/runtime 检查 | low |
| `research` | coding 检查 + 智谱 web MCP | low |
| `browser` | research + Playwright 自动化（显式选择） | high |
| `full` | 完整能力（含 browser） | high |

`dotf agents -c` 默认使用低风险 `research` profile，不启用浏览器自动化，也不需要 browser consent。`browser` / `full` 只能通过显式 `--profile` 或外置 overlay 选择。

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
PYTHONPATH=scripts python3 -m dotf_core.overlays init
```

命令只写 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/00-local.yaml`。多个 `*.yaml` 按 UTF-8 文件名字节序加载，mapping 递归合并，后文件的 scalar/list 替换前文件；所有文件在合并前后均严格校验。可覆盖默认 profile、server 选择、browser 本机设置与 Codex `local_toml`。

旧 `agents/env/local.yaml`、`local-*.yaml`、`local/*.yaml` 与 `agents/vendors/codex/config.local.toml` 仅作为只读迁移输入，读取时告警。显式迁移：

```shell
PYTHONPATH=scripts python3 -m dotf_core.overlays migrate
```

## Browser MCP

- 默认 provider：`@playwright/mcp`（`npx -y @playwright/mcp@0.0.80`）
- 默认 **隔离** user-data-dir：`/tmp/agent-env/browser/profile`
- 截图 / trace 建议目录：`/tmp/agent-env/browser/artifacts`（**不要提交**）
- Chrome DevTools / 真实主 profile：仅 local override 显式 opt-in，doctor 会标 high risk

启用流程：

```shell
scripts/agents/sync.sh cursor --env-only --profile browser
python3 scripts/agents/doctor.py --profile browser --tool cursor --verbose
```

同步后重载或重启对应 agent 客户端，让新的 MCP 配置生效。显式 `browser` / `full` 会生成 `playwright`；默认 `research` 与显式 `coding` 均不启用浏览器自动化。

Smoke test：

1. 在启用 browser profile 的 agent 中打开 `https://example.com`。
2. 读取页面 snapshot，确认能看到 Example Domain。
3. 如需视觉检查，再请求 screenshot：**不要传 `filename`**（自动落到 `--output-dir`）；若必须命名只传 basename（如 `example.png`），不要绝对路径。
4. 若 provider 启动失败，先运行 `npx playwright install chromium`；Linux 缺系统依赖时再按 Playwright 提示运行 `npx playwright install-deps`。

截图、trace、downloads、浏览器 profile 都可能包含私有信息；不要提交到仓库，也不要把包含登录态的真实 profile 作为默认配置。Playwright MCP 在传入自定义 `filename` 时可能把文件写到工作区根目录（绕过 `--output-dir`），因此默认省略 `filename`。headed/xvfb、`browser_executable`、CDP endpoint、真实 profile 只能通过 XDG external overlay 或环境变量显式 opt-in。

## 安全

- 仓库只存变量**名**与占位符（Cursor/Kiro: `${ZHIPU_API_KEY}`；OpenCode: `{env:ZHIPU_API_KEY}`；Kimi HTTP: `bearerTokenEnvVar`）
- 真实密钥只放环境变量或系统 keychain
- **例外：ZCode 不展开 `${VAR}`**。`dotf agents -c --tool zcode` 会把 `ZHIPU_API_KEY` 展开进本机 `~/.zcode/cli/config.json`（HTTP `Authorization` 与 stdio `env`）；仓库模板仍只保留占位符。缺密钥时 sync 失败，不留下无法连接的占位符配置。
- 本机路径只放 XDG external overlay；仓库 local 文件仅为只读迁移输入
- doctor 会扫描明显 secret / 内网 URL，且**永不打印** secret 值
- Kimi Code **不会**展开 `${ENV}`。HTTP 必须用 `bearerTokenEnvVar`（写成 headers 字面量会收到智谱 `{"code":401,...}`）；stdio `env` 里的 `${ZHIPU_API_KEY}` 会渲染成 `sh -c`，在启动时从进程环境映射为 `Z_AI_API_KEY`。
- MiniMax：`MINIMAX_API_KEY`（本仓库 Codex 打**国内** `api.minimaxi.com`）与 Pi 海外 provider `minimax`（`api.minimax.io`）**不是一回事**；国内 key 用 Pi 须走 `minimax-cn` / `MINIMAX_CN_API_KEY`。专题：`repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`
- Kimi（Pi）：`KIMI_API_KEY` → 内置 provider `kimi-coding`；`dotf pi -c` 会写入 `auth.json` 的 `$KIMI_API_KEY` 引用

## 与工具配置的关系

Cursor / Kiro / OpenCode / Kimi Code / ZCode 的 MCP 片段由本目录生成并安全合并。CLI choices 以 `vendors.yaml` 为唯一来源；Codex / Pi / DSH 保留显式 skip 能力：

```shell
scripts/agents/sync.sh cursor|kiro|opencode|codex|kimi-code|pi|zcode|dsh|all
```

Codex / Pi 当前无稳定 MCP 入口，DSH 使用 profile-local MCP 配置；sync/doctor 对这些工具记为 `skip`（共享 skills 仍走 `agents/`）。

各工具 home 配置中的 MCP 段由 sync 写入；仓库内 `agents/vendors/*/…` 是安全的 committed 模板；普通 runtime sync 永不更新它们。请改 `agents/env/mcp/` 后通过受审查的维护流程更新模板，不要让本机 overlay 回流仓库。

### Doctor 安全边界

`python3 scripts/agents/doctor.py` 是唯一受支持的 Agent doctor CLI/renderer；`doctor_impl.py` 仅保留兼容导入，不维护独立检查逻辑。Doctor 与同步共用 SyncPlan、runtime/MCP ownership manifest 和 adapters，并以相同 canonical checks 生成 text/JSON。

敏感备份默认保留 **7 天**。版本化策略位于 `agents/env/security.yaml` 的 `sensitive_backups.retention_days`，可在提交并审查该安全配置后覆盖。每个敏感备份目录可放置 `.dotf-backup.json` 元数据（`version: 1`、`sensitive: true`、带时区的 `created_at`）；doctor 只读取该元数据判断过期，不读取或打印备份内容。

## Runtime、模板与恢复

新机先用 `PYTHONPATH=scripts python3 -m dotf_core.overlays init` 在 XDG 配置目录创建外置 overlay；存在旧 `agents/env/local*.yaml` 或 Codex local TOML 时，用 `PYTHONPATH=scripts python3 -m dotf_core.overlays migrate` 显式迁移。旧文件只作为只读输入并告警，不会写入 committed 模板。默认 `research` 是低风险选择；只有显式 `--profile browser|full` 或外置 overlay 才能启用 high-risk browser 能力。

runtime sync 通过 managed ownership manifest 只更新 dotf 拥有的 skill 文件与 MCP server id。unowned、local modification、unexpected symlink 或 malformed target 都是保守的 conflict/fail，用户内容保持不变。多目标写入先 staging，再以 transaction journal 提交；失败逆序 rollback，`failed-rollback` 时保留 journal 和备份供人工恢复。

仓库模板只能由维护命令显式生成，不能由普通 sync 或本机 overlay 更新：

```shell
python3 scripts/agents/generate_templates.py
python3 scripts/agents/generate_templates.py --check
git diff --exit-code -- agents/vendors/*
```

CI 会从 committed safe sources 重新生成后要求 `git diff --exit-code`，同时对 git-tracked Agent/source 文本执行带 `rule_version`、`scanned`、`skipped`、`findings` 证据的 secret scan。
