# Skill / MCP 的撤除必须是 Desired Set + prune

只改 HOME 里的 skill 目录或 mcp.json，下次 sync 会按编目装回来。remove 必须在同一次计划里先改本机 Desired Set（XDG overlay），再 prune owned 目标；TUI 和 CLI 都不提供「只抠文件」的半截操作。
