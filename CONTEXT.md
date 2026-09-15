# Dotfiles

本机开发环境的模块化安装、配置与 Agent 运行时同步。TUI 是同一条执行管线的浏览与确认皮肤，不是第二套控制面。

## Language

### Inventory

**Module**:
`modules.yaml` 里的一条注册项，是工具与配置在 TUI 主清单中的一行。
_Avoid_: 工具, 包, package, 软件（作为清单行）, 配置项目, 项目（指单个 Module 时）

**Skill**:
一条可分发技能；本机上管理的就是这份制品本身。apply / remove 以机器为粒度，所有读取共享 skills 目录的工具一起生效。
_Avoid_: 插件, prompt, command（command 是另一种制品）

**Skill Catalog**:
`agents/skills.yaml`，全部 Skill 的唯一编目，**按 group 组织**。组声明 `type`（一手/第三方）与第三方 `source`/`package`，成员只写 id（或 `- id` + `optional: true` 映射）。**没有 default 字段**：编目内即自动全量安装，`optional: true` 条目是唯一例外（默认不装、可经 overlay 按需启用）；不想保留就注释掉条目。desired_set / lock 校验 / overlay / CLI 都读它。
_Avoid_: skills-defaults（旧名）, 打平列表, skill 清单（含糊）

**First-Party Skill**:
来源是仓库内 `agents/skills/<id>/` 的 Skill。编目里 `type: first-party`；不带 hash/revision，目录即真相，但目录必须被编目覆盖。
_Avoid_: 自家 skill, 内置 skill, vendor 副本

**Third-Party Skill**:
来源由 lock 固定的 Skill，编目里 `type: third-party`，并声明 `source: registry | github` 与 `package`；revision / hash / license / audit 只在 lock，编目只引用。
_Avoid_: 外部 skill, 上游 skill（作为制品名）

**Locked Skill**:
第三方 Skill 中 lock 已批准其不可变 revision 的那条。被注释出编目的 Locked Skill 不自动装，也不能经 overlay 引用；要重新启用需取消注释。
_Avoid_: 未锁定 skill, 浮动上游

**Skill Group**:
编目的组织与 CLI 单位：组声明来源属性（`type` / `source` / `package`），成员写 id。仓库一手 skill 进 `dotfiles`，第三方按来源分。group 不承载信任模型（那是 `type`）。组名兼作 CLI 展开单位，`dotf skills -i <group>` 装整组；名字解析先匹配 group、再匹配 skill id、最后透传 npx。
_Avoid_: type（两者正交）, 包, 命名空间（含糊）

**Skill Layout**:
Skill 的安装目标，清单在 `src/agents/layouts.py`：`shared`（`~/.agents/skills`）、`kiro`（`${KIRO_HOME:-~/.kiro}/skills`）、`claude`（`~/.claude/skills`）。每个 layout × 来源（一手 / 第三方 / OpenSpec）派生各自的 owner 前缀，因为 runtime manifest 是全 layout 共用的一份，前缀必须互不重叠。Kiro 在 `SKILL.md` 末尾补 `$ARGUMENTS`；Claude Code 自己消费参数，走与 shared 相同的渲染。
_Avoid_: 工具（那是 vendor 身份，不是安装目标）, 镜像（Kiro 只是其一）, target root（实现细节）

**Kind**:
`modules.yaml` 里模块的物种声明：`binary` 负责把软件装到本机（必须声明 install 且有 install handler），`config` 只部署配置（不得声明 install、不得有 install handler；专用 `config.sh` 仍是合法配置触点）。`artifact` 为保留值（未来制品型模块），当前校验拒绝。registry validate 强制 kind ↔ install ↔ Handler 对齐。
_Avoid_: 物种（口语）, 用 install 字段隐式表达, 第二引擎（指 agents 引擎时）

**TUI**:
显式命令 `dotf tui` 打开的交互皮肤：Modules 一区，Skill 一区。不占领无参数 `dotf`，v1 不替换编号点选。
_Avoid_: 控制面, 新安装器, 默认 `dotf`

### Actions

**uninstall**:
模块上与 install 对称的反动作。必须由该模块声明并提供 handler；未声明则没有这个动作。
_Avoid_: 删除, remove（作动作名）, 卸载（当它同时指软件和配置时）, 猜测卸法

**deconfig**:
模块上与 config 对称的反动作：只撤 owned 且内容仍等于上次受管 hash 的目标。可走通用所有权撤回，不必每模块手写。
_Avoid_: uninstall config, 删除配置, 清目录

**apply**:
Skill 的正动作：写入 Desired Set 并 sync，使制品存在。CLI 入口与 TUI 按钮必须成对出现。
_Avoid_: install, config（用在 Skill 上时）

**remove**:
Skill 的反动作：移出 Desired Set 并 prune owned 目标；两步同一次计划，缺一不可。
_Avoid_: uninstall, deconfig（用在 Skill 上时）, 只删文件

**re-apply**:
对已有动作再跑一次（模块的 install / config，或 Skill 的 apply）。不是新的生命周期动词。
_Avoid_: update, 更新（作为动作名）

**Conflict**:
owned 目标的内容或 mode 已不等于上次受管 hash。默认 fail closed：正向动作报告并保留，deconfig / remove 必须留下它并报告，不得当未修改目标撤掉。出口是 `--on-conflict=backup`：先把当前内容备份到 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/` 再覆写。不涵盖 Unowned Target、不安全类型、manifest 异常、所有权身份不符、越界目标，也不影响任何反向动作。
_Avoid_: drift（当已能判定是 Conflict 时）, 损坏, 自动覆盖, 用 Conflict 指无所有权文件

**Unowned Target**:
计划要写的路径上已有常规文件，但 managed manifest 没有对应 agents ownership。字节已等于将写入内容时可静默登记 ownership（adopt）；字节不等价时默认留下，不得经 `--on-conflict` 解除。
_Avoid_: Conflict（那是已 owned 的漂移）, 外来文件（含糊）, 无主（口语）

**Takeover**:
把 Unowned Target（内容不等价）先 backup 再写入受管字节并首次登记 ownership 的显式动作。与 Conflict 的 `--on-conflict=backup` 分家；CLI 为 `--takeover=backup`（环境变量 `DOTF_TAKEOVER`）。TTY 在计划确认之外对可接管项做一次汇总二次确认（写到控制终端 `/dev/tty`，不依赖 Handler stdout 是否被 Executor 捕获）；非 TTY 必须带显式 flag，默认跳过。一次确认覆盖整次 agents sync（一手 / defaults / OpenSpec）。
_Avoid_: on-conflict（管 owned 漂移）, adopt（只用于字节已等价）, 强制覆盖

### Scope

**Desired Set**:
这台机器同步之后应该存在的 Skill。默认 = 编目内非 optional id ∪ overlay 显式启用，再减去 overlay 停用。不含 OpenSpec 生成的 skill，不含未锁定第三方；optional 编目条目只有被 overlay 启用才进入。
_Avoid_: catalog（那是仓库编目）, 清单（含糊）

**Dependent**:
`depends_on` 指向某模块的另一个模块。只要 Dependent 仍在，被依赖模块的 uninstall 必须拒绝。
_Avoid_: 级联卸载, 反向依赖（当已能说 Dependent 时）

**Uninstall Handler**:
uninstall 动作的 Handler。v1 只要求管线存在；先覆盖用户级、边界清楚的单二进制模块。`system` / `homebrew` / `sdk` / Docker 暂无此动作。
_Avoid_: 通用卸包, 猜测卸法

### Anatomy

**Handler**:
一个 Module 的约定式操作脚本，位于 `scripts/modules/<name>/`（install.sh / config.sh / doctor.sh / uninstall.sh），由 Executor 按名发现与调用；泛化原 Uninstall Handler。
_Avoid_: 操作文件, 模块脚本, tools/<name>.sh 散件（已并入 Handler 目录）

**Executor**:
约定式调度层：读 modules.yaml，按名发现并调用 Handler 与 config 部署，自身不含模块专属逻辑。
_Avoid_: 操作文件执行器, 安装器, 调度器（与 planner 混称）

### Surfaces

**CLI**:
脚本与自动化的对外入口。模块反动作与 Skill 的 apply / remove 必须先有 CLI，TUI 只调用它们。
_Avoid_: 旧入口, 旁路, 仅 TUI 能做的动作
