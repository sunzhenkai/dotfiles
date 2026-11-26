# Antigravity 配置（agy CLI + skills 桥接）

本目录的 `skills.json` 是 Antigravity 全局 skill 发现桥接文件的源；registry 里 `antigravity.config` 声明它是唯一真相，部署有两个入口，写的是同一目标、同一份 ownership：

- `dotf agents -c` 的 `antigravity bridge` 阶段（`src/agents/antigravity_bridge.py`，检测到 Antigravity 才写入，否则跳过）。
- `dotf agy -c` / `dotf antigravity -c`（`agy` 是模块别名），走通用 config handler。

桥接本身：

- `skills.json` → `~/.gemini/config/skills.json`（只读受管 `0644`、`strategy: render`），将 `~/.agents/skills` 挂载到 Antigravity 的全局 skill 发现路径，不重复拷贝第三份 skill 树，也不触碰 `~/.gemini/config/{plugins,projects,sidecars}/`。
- 源文件里的 `path` 写成 `@HOME@/.agents/skills` 占位符，由 `src/dotf_core/config_producers.py` 的 producer 在部署时换成实际 HOME。原因：hub server 2.34.0 只接受绝对路径，`~/.agents/skills` 会被它静默跳过（`customization.go:617` 报 `must be an absolute path`），尽管它自带的 `json_configs.md` 声称支持 `~/`。本机也用 A/B 实测确认：绝对路径下 skill 列表随 `~/.agents/skills` 内容变化，`~/` 下报错且不生效。
- 全局指令由 `dotf agents -c`（`agents/instructions/install.yaml`）安装到 `~/.gemini/GEMINI.md`。

约定（ADR 0016 / 0017）：

- 本仓库不声明 LLM provider / 模型 / 密钥，也不托管 MCP 配置或本地登录态。
- `dotf agy -i` / `dotf antigravity -i` 安装 Antigravity CLI（`agy`）。
