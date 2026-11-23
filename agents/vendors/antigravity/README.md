# Antigravity 配置（agy CLI + skills 桥接）

本目录通过 `dotf antigravity -c` 部署 Antigravity 全局 skill 发现桥接文件：

- `skills.json` → `~/.gemini/config/skills.json`（只读受管 `0644`、`strategy: copy`），将 `~/.agents/skills` 挂载到 Antigravity 的全局 skill 发现路径，不重复拷贝第三份 skill 树，也不触碰 `~/.gemini/config/{plugins,projects,sidecars}/`。
- 全局指令由 `dotf agents -c`（`agents/instructions/install.yaml`）安装到 `~/.gemini/GEMINI.md`。

约定（ADR 0016 / 0017）：

- 本仓库不声明 LLM provider / 模型 / 密钥，也不托管 MCP 配置或本地登录态。
- `dotf antigravity -i` 安装 Antigravity CLI（`agy`）。
