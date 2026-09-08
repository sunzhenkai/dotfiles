# module-lifecycle Specification

## Purpose
TBD - created by archiving change overhaul-dotfiles-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: 约定式模块动作处理器
系统 SHALL 从 `scripts/modules/<name>/<action>.sh` 约定位置发现 install、config、doctor、uninstall 处理器，并延迟加载当前计划需要的处理器。deconfig MAY 使用通用实现而无模块专用脚本。注册表 SHALL 只声明能力和元数据，不得保存函数名、脚本路径或任意执行命令。每个动作结果确定后，runner SHALL 同步维护 `XDG_STATE_HOME/dotf/modules-state.yaml`（schema 见 `dotf-modules-state` spec）：install / config 成功后写 `last_at` 与（若可得）`version` / `manifest_managed`；deconfig 成功后删除 `config` 字段；uninstall 成功后删除该模块在 state 中的全部字段。state 写入 SHALL 走原子写；写入失败 SHALL 记 warn 而不把动作从 `changed` 降级为 `failed`。

#### Scenario: 加载单个安装处理器
- **WHEN** 计划仅包含模块 `sdk` 的 install 动作
- **THEN** runner SHALL 只加载该模块的 install 处理器及其公共库

#### Scenario: 声明与处理器不一致
- **WHEN** 模块声明 install 能力但缺少对应处理器
- **THEN** 注册表或运行前校验 SHALL 以非零结果失败并指出模块

#### Scenario: 未声明的处理器
- **WHEN** 模块目录存在 config 处理器但注册表未声明 config 能力
- **THEN** 校验 SHALL 报告不一致且不得隐式开放该能力

#### Scenario: 声明 uninstall 但缺少脚本
- **WHEN** 模块声明 uninstall 但缺少 `uninstall.sh`
- **THEN** 注册表或运行前校验 SHALL 以非零结果失败并指出模块

#### Scenario: install 成功写 state
- **WHEN** 模块 `grepom` 的 install 动作结果为 `changed` 或 `unchanged`
- **THEN** runner SHALL 同步写 `modules.grepom.install.last_at`
- **THEN** 若 handler 输出包含 version SHALL 写 `install.version`

#### Scenario: config 成功写 state
- **WHEN** 模块 `nvim` 的 config 动作结果为 `changed` 或 `unchanged`
- **THEN** runner SHALL 同步写 `modules.nvim.config.last_at` 与 `modules.nvim.config.manifest_managed`（取自当前 manifest 该模块 owner 的目标数）

#### Scenario: deconfig 清 config 字段
- **WHEN** 模块 `nvim` 的 deconfig 动作结果为 `changed`
- **THEN** runner SHALL 同步删除 `modules.nvim.config`
- **THEN** `modules.nvim.install` SHALL 保持不变

#### Scenario: uninstall 清空
- **WHEN** 模块 `grepom` 的 uninstall 动作结果为 `changed`
- **THEN** runner SHALL 同步删除 `modules.grepom` 下所有字段

#### Scenario: 写 state 失败不致命
- **WHEN** 写 `modules-state.yaml` 临时文件失败
- **THEN** runner SHALL 记录 warn 并继续返回该动作原始结果
- **THEN** SHALL NOT 将动作从 `changed` 降级为 `failed`

### Requirement: 统一动作结果
runner SHALL 将每个动作结果规范化为 `changed`、`unchanged`、`skipped` 或 `failed`，并记录模块名、动作、耗时和脱敏原因。任一 failed SHALL 导致整体非零退出。

#### Scenario: 目标已满足
- **WHEN** 处理器检测到安装或配置目标已经满足
- **THEN** 动作结果 SHALL 为 unchanged

#### Scenario: 动作改变环境
- **WHEN** 处理器成功安装工具或更新配置
- **THEN** 动作结果 SHALL 为 changed

#### Scenario: 动作失败
- **WHEN** 处理器无法完成请求
- **THEN** 动作结果 SHALL 为 failed
- **THEN** runner SHALL 保留非零失败语义

### Requirement: 模块动作幂等与确认归属
模块处理器 SHALL 支持重复执行；相同输入下目标已满足时 SHALL 不重复产生破坏性修改。用户确认 SHALL 由顶层 orchestrator 负责，模块处理器不得另行产生无法统一控制的交互确认。

#### Scenario: 重复配置
- **WHEN** 用户连续两次应用相同配置
- **THEN** 第二次 SHALL 不重复备份或重写正确目标
- **THEN** 第二次结果 SHALL 为 unchanged

#### Scenario: 非交互执行
- **WHEN** orchestrator 已通过 `--yes` 授权执行
- **THEN** 模块处理器 SHALL NOT 再等待交互输入

### Requirement: 配置安全默认实现
系统 SHALL 提供公共 symlink 配置实现：正确链接返回 unchanged；错误或损坏链接安全替换；普通文件或目录在替换前备份；缺失的父目录自动创建。特殊 copy、template、merge、submodule 或 sync 行为 SHALL 位于模块专用处理器中。

#### Scenario: 普通配置文件已存在
- **WHEN** symlink 配置目标是普通文件或目录
- **THEN** 系统 SHALL 将其备份到用户备份目录后创建链接

#### Scenario: 正确链接已存在
- **WHEN** 目标链接已指向期望源
- **THEN** 系统 SHALL 不修改目标并返回 unchanged

### Requirement: uninstall 须有约定 handler
系统 SHALL 从 `scripts/modules/<name>/uninstall.sh` 发现 uninstall 处理器。模块只有在注册表声明 uninstall 且该处理器存在时才具备该动作。uninstall SHALL 撤掉该模块 install 落到本机的软件，并支持重复执行：目标已不在时返回 unchanged。系统 SHALL NOT 猜测通用卸包命令。

#### Scenario: 声明且存在则可计划
- **WHEN** 模块声明 uninstall 且存在对应处理器
- **THEN** planner SHALL 允许对该模块生成 uninstall 动作

#### Scenario: 缺少 handler 不得猜测
- **WHEN** 模块未声明 uninstall 或缺少处理器
- **THEN** 对该模块请求 uninstall SHALL 在执行前失败
- **THEN** SHALL NOT 调用 brew、mise 或其它猜测出的卸包命令

#### Scenario: 重复 uninstall 幂等
- **WHEN** 用户对已成功卸载的模块再次 uninstall
- **THEN** 结果 SHALL 为 unchanged
- **THEN** SHALL NOT 再产生破坏性修改

### Requirement: deconfig 撤 owned 未漂目标
系统 SHALL 提供与 config 对称的 deconfig 动作。deconfig SHALL 只撤该模块 managed manifest 中 owned 且内容仍等于上次受管 hash 的目标，并更新 manifest。Conflict 与 unmanaged 路径 SHALL 留下并报告。deconfig MAY 使用通用所有权撤回，不必每模块手写处理器。重复 deconfig 在已无 owned 目标时 SHALL 返回 unchanged。

#### Scenario: 未修改受管文件被撤
- **WHEN** 模块配置目标 owned 且 hash 未漂
- **THEN** deconfig SHALL 移除这些目标
- **THEN** SHALL 更新 managed manifest

#### Scenario: Conflict 留下
- **WHEN** owned 目标内容不等于上次受管 hash
- **THEN** deconfig SHALL 报告 Conflict
- **THEN** SHALL NOT 删除或覆盖该目标

#### Scenario: 不删 unmanaged
- **WHEN** 目标目录中存在未记录在 managed manifest 的文件
- **THEN** deconfig SHALL NOT 删除这些文件

### Requirement: 有 Dependent 时拒绝 uninstall
当任一其它模块通过 `depends_on` 直接或传递依赖目标模块，且该依赖方仍在本次卸载范围之外时，planner SHALL 拒绝 uninstall，列出 Dependent，且 SHALL NOT 级联卸载。deconfig SHALL NOT 仅因存在 Dependent 而被拒绝。

#### Scenario: 依赖方仍在则拒绝
- **WHEN** 用户请求 uninstall `sdk`，且 `golang` 依赖 `sdk` 且不在同一计划中卸载
- **THEN** planner SHALL 在执行前失败
- **THEN** 错误 SHALL 列出 `golang` 或其它 Dependent
- **THEN** SHALL NOT 卸载 `sdk`

#### Scenario: 同计划卸掉依赖方后允许
- **WHEN** 用户在同一计划中先卸载所有 Dependent 再卸载被依赖模块，且拓扑合法
- **THEN** planner MAY 生成该计划
- **THEN** Dependent 的 uninstall SHALL 先于被依赖模块

#### Scenario: deconfig 不受 Dependent 阻断
- **WHEN** 用户对 `sdk` 请求 deconfig（若其具备 config）且存在 Dependent
- **THEN** planner SHALL NOT 仅因 Dependent 拒绝 deconfig
