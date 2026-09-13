# 移除 MCP 配置体系

仓库曾维护一套完整的 MCP（Model Context Protocol）配置分发体系：`agents/env/mcp/servers.yaml` 声明 5 个 server（web-search-prime / web-reader / zread / playwright / zai-vision），经 vendor 能力矩阵（`agents/env/vendors.yaml`）与 per-tool adapter 渲染，把 cursor / kiro / opencode / kimi-code / zcode 五个目标的结构化配置安全合并，配套 sync plan / 所有权 manifest / transaction journal / doctor 检查 / TUI MCP tab / 金样测试与 openspec spec。

决定：整体移除。MCP server 的选择与各工具的密钥展开强耦合（runtime placeholder、`bearerTokenEnvVar`、`literal-at-apply` 三种 secret mode 并存），维护成本高于实际收益；这些配置由各工具侧自行维护，仓库不再做统一真相源。随之移除的还有以 Playwright MCP 为唯一 provider 的 browser 自动化能力（`agents/env/browser.yaml`、doctor 的 `check_browser` / deep probe、`agents-browser` spec）。

保留：`agents/env` 下的 profiles / env schema / tools / security（doctor 的 env / tools / security 检查继续消费，profile 由 `mcp/profiles/` 迁至 `agents/env/profiles/` 并剥离 `mcp_servers` 字段）；codex / opencode / pi 的 provider 与密钥声明（`ZHIPU_API_KEY` 等仍由 env schema 声明、被 provider 配置引用）；skills / instructions 的 Desired Set、managed manifest 与 conflict 语义不受影响。

备选：只收敛漂移（把本机 `@latest` 重新同步为钉版本）保留体系——这只治标，secret-mode 矩阵与多目标事务的复杂度依旧由仓库承担，否决；把 claude-code 纳入管理再一起治理——新增 adapter 是纯增量工作且方向与「降维护」相反，否决。

后果：`dotf agents mcp apply|remove`、`dotf agents -c --tool`、`sync.sh --env-only`、TUI 的 MCP tab、`agents-mcp-manifest.json` 状态文件全部消失；已安装目标（`~/.cursor/mcp.json` 等）由一次性机器侧清理摘除，之后由各工具自行管理。若未来要恢复 MCP 分发，git 历史与本 ADR 描述的耦合面是重新评估的起点。
