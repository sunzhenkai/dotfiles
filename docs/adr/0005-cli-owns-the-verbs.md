# 没有 CLI 动词的动作不许出现在 TUI

TUI 是皮肤。模块的 uninstall / deconfig，以及 Skill / MCP 的 apply / remove，必须先成为 planner 一等 CLI 动作（含 journal 与 retry），TUI 只点选并提交同一份计划。否则脚本、CI 和无 TTY 环境会被迫走第二条控制面。
