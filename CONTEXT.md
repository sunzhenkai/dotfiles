# Dotfiles

本机开发环境的模块化安装、配置与 Agent 运行时同步。TUI 是同一条执行管线的浏览与确认皮肤，不是第二套控制面。

## Language

### Inventory

**Module**:
`modules.yaml` 里的一条注册项，是工具与配置在 TUI 主清单中的一行。
_Avoid_: 工具, 包, package, 软件（作为清单行）

**Skill**:
一条可分发技能；本机上管理的就是这份制品本身。apply / remove 以机器为粒度，所有读取共享 skills 目录的工具一起生效。
_Avoid_: 插件, prompt, command（command 是另一种制品）

**Locked Skill**:
第三方 Skill：lock 已批准其不可变 revision。TUI/CLI 可以 apply 它，即使它不在默认选中列表里。
_Avoid_: 未锁定 skill, 浮动上游

**MCP Server**:
编目里声明的一条 MCP 服务，是 Agent 区可选行的来源。
_Avoid_: MCP, 工具（指 server 本身时）

**MCP Entry**:
某个目标工具结构化配置文件里的一条具名 server 记录。默认按工具增删这一条，不是删整份文件，也不是默认全工具一起关。
_Avoid_: MCP 配置（含糊）, 整个 mcp.json

**TUI**:
显式命令 `dotf tui` 打开的交互皮肤：Modules 一区，Skill 与 MCP Entry 一区。不占领无参数 `dotf`，v1 不替换编号点选。
_Avoid_: 控制面, 新安装器, 默认 `dotf`

### Actions

**uninstall**:
模块上与 install 对称的反动作。必须由该模块声明并提供 handler；未声明则没有这个动作。
_Avoid_: 删除, remove（作动作名）, 卸载（当它同时指软件和配置时）, 猜测卸法

**deconfig**:
模块上与 config 对称的反动作：只撤 owned 且内容仍等于上次受管 hash 的目标。可走通用所有权撤回，不必每模块手写。
_Avoid_: uninstall config, 删除配置, 清目录

**apply**:
Skill 或 MCP Entry 的正动作：写入 Desired Set 并 sync，使制品或 Entry 存在。CLI 入口与 TUI 按钮必须成对出现。
_Avoid_: install, config（用在 Skill / MCP 上时）

**remove**:
Skill 或 MCP Entry 的反动作：移出 Desired Set 并 prune owned 目标；两步同一次计划，缺一不可。
_Avoid_: uninstall, deconfig（用在 Skill / MCP 上时）, 只删文件

**re-apply**:
对已有动作再跑一次（模块的 install / config，或 Skill / MCP 的 apply）。不是新的生命周期动词。
_Avoid_: update, 更新（作为动作名）

**Conflict**:
owned 目标的内容已不等于上次受管 hash。deconfig / remove 必须留下它并报告，不得当未修改目标撤掉。
_Avoid_: drift（当已能判定是 Conflict 时）, 损坏

### Scope

**Desired Set**:
这台机器同步之后应该存在的 Skill 与 MCP Entry。默认 = 一手 catalog ∪ 默认选中的第三方 ∪ overlay 显式启用，再减去 overlay 停用。不含 OpenSpec 生成的 skill，不含未锁定第三方。
_Avoid_: catalog（那是仓库编目）, 清单（含糊）

**Dependent**:
`depends_on` 指向某模块的另一个模块。只要 Dependent 仍在，被依赖模块的 uninstall 必须拒绝。
_Avoid_: 级联卸载, 反向依赖（当已能说 Dependent 时）

**Uninstall Handler**:
模块自己声明的撤软件实现。v1 只要求管线存在；先覆盖用户级、边界清楚的单二进制模块。`system` / `homebrew` / `sdk` / Docker 暂无此动作。
_Avoid_: 通用卸包, 猜测卸法

### Surfaces

**CLI**:
脚本与自动化的对外入口。模块反动作与 Skill / MCP 的 apply / remove 必须先有 CLI，TUI 只调用它们。
_Avoid_: 旧入口, 旁路, 仅 TUI 能做的动作
