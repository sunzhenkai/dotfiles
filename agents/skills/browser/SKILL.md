---
name: browser
description: 浏览器自动化（Playwright MCP）使用规范：导航、页面快照、截图与产物路径。在启用 browser profile、调用浏览器 MCP、截图或视觉调试时使用。
---

# 浏览器

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

使用 Playwright 等浏览器自动化能力时遵循本规范。策略真相源见 `agents/env/browser.yaml`。

## 截图产物

- 截图、trace、downloads **不得**写入工作区。
- MCP 已配置 `--output-dir` → `/tmp/agent-env/browser/artifacts`（与 `artifact_dir` 一致）。
- **默认不要传 `filename`**：让 MCP 自动命名（`page-{timestamp}.png`），文件会进 `--output-dir`。
- 若必须命名：只传 **basename**（如 `example.png`），禁止绝对路径、禁止带目录分隔符。
- 自定义 `filename` 在部分 Playwright MCP 版本会落到工作区根目录并绕过 `--output-dir`；绝对路径同样会绕过。
- 需要读图时，用工具返回的绝对路径（可在 `/tmp/...`）；不要为了「方便 Read」把截图拷进仓库。

## 使用要点

1. 优先读页面 snapshot；只有需要视觉确认时再截图。
2. 默认使用隔离 profile，不要连接用户主浏览器或真实登录态，除非用户明确要求。
3. 截图可能含私有/内部信息；展示后勿建议提交仓库。
