# Cursor MCP

`agents/vendors/cursor/mcp.json` 是 **agents/env 生成物**。请改 `agents/env/mcp/` 后运行：

```shell
dotf agents -c
scripts/agents/sync.sh cursor
```

默认 profile 为 `research`（智谱 web-search / web-reader / zread）。  
浏览器自动化需 `--profile browser`。

密钥使用占位符 `${ZHIPU_API_KEY}`，在环境变量中设置真实值。详见 `agents/env/README.md`。
