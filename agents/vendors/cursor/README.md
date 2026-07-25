# Cursor MCP

`agents/vendors/cursor/mcp.json` 是 **agents/env 生成物**。请改 `agents/env/mcp/` 后运行：

```shell
dotf agents -c
scripts/agents/sync.sh cursor
```

默认 profile 为 `browser`（智谱 web MCP + Playwright）。
只要搜索不要浏览器时用 `--profile research`。

密钥使用占位符 `${ZHIPU_API_KEY}`，在环境变量中设置真实值。详见 `agents/env/README.md`。
