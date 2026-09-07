# v1 先打通 uninstall 管线，不追求全模块能卸软件

没有 handler 就猜测卸法会伤到底座。v1 先把注册表能力、planner / CLI / TUI、Dependent 拒绝和 journal / retry 接好；handler 从用户级单二进制模块写起。`system` / `homebrew` / `sdk` / Docker 标「不可卸载」。没有 uninstall 的模块仍可 config / deconfig / doctor / 看状态，Skill / MCP 的 apply / remove 不依赖模块 handler。
