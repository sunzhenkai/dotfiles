# 不新增 update 生命周期动词

「更新」容易和升级软件包、pull 仓库、升 lock revision 混在一起。模块再跑 install / config，Skill / MCP 再跑 apply，仓库用已有 `dotf pull`；第三方 revision 仍由维护者改 lock。TUI 可以对 drifted 行放重新执行按钮，但不创造第四/第五种动作名。
