# Cursor MCP

Cursor MCP 只由 agents sync 写入 `~/.cursor/mcp.json`；`dotf cursor` 模块只负责安装 CLI。`agents/vendors/cursor/mcp.json` 是不参与部署的安全生成参考，用于 drift/占位符检查。请改 `agents/env/mcp/` 后运行：

```shell
dotf agents -c
scripts/agents/sync.sh cursor
```

默认 profile 为低风险 `research`（不含浏览器自动化）。只有显式选择 `--profile browser` 或 `--profile full` 时才启用 Playwright 等高风险 browser 能力。

密钥使用占位符 `${ZHIPU_API_KEY}`，在环境变量中设置真实值。详见 `agents/env/README.md`。
