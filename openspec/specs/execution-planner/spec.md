# execution-planner Specification

## Purpose
TBD - created by archiving change overhaul-dotfiles-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: 所有入口共享执行计划
系统 SHALL 使用同一 planner 为 `init`、全量动作、交互选择、显式模块动作和 retry 生成带版本的完整执行计划。计划 SHALL 在执行前完成严格注册表、能力、OS、profile、依赖和动作 schema 校验。执行器 SHALL 仅接受 planner 成功产生且具有唯一成功标记、受支持版本和完整字段的计划；任何生成、读取或校验异常 SHALL fail-closed。

#### Scenario: 不同入口选择同一模块集合
- **WHEN** 两个入口在相同 OS、profile、模块和动作输入下生成计划
- **THEN** 两个计划 SHALL 包含相同且顺序一致的动作

#### Scenario: 计划校验失败
- **WHEN** 输入包含未知模块、无效 profile、不支持动作能力或无效注册表
- **THEN** planner SHALL 在执行任何动作前以非零结果失败

#### Scenario: Planner 异常退出
- **WHEN** planner 非零退出、没有产生完整计划或输出被截断
- **THEN** 执行器 SHALL 非零退出
- **THEN** SHALL NOT 执行任何动作

#### Scenario: 计划结构无效
- **WHEN** 计划缺少成功标记、版本或必要字段，或包含未知/重复动作记录
- **THEN** 执行器 SHALL 在动作开始前拒绝该计划

#### Scenario: 注册表严格校验失败
- **WHEN** 注册表包含缺失 handler、非法部署策略或冲突安全元数据
- **THEN** planner SHALL 非零失败
- **THEN** SHALL NOT 产生可执行计划

### Requirement: 依赖展开与稳定拓扑排序
planner SHALL 递归展开模块 `depends_on`，保证依赖动作先于依赖方，并检测未知依赖和依赖环。无依赖约束的模块 SHALL 按注册表声明顺序保持稳定。

#### Scenario: 递归依赖
- **WHEN** 模块 A 依赖 B 且 B 依赖 C
- **THEN** 计划中的相关动作顺序 SHALL 为 C、B、A

#### Scenario: 依赖环
- **WHEN** 注册表形成 A → B → A 的依赖环
- **THEN** planner SHALL 以非零结果失败并指出环中的模块

#### Scenario: 未知依赖
- **WHEN** 模块声明不存在的依赖
- **THEN** planner SHALL 在执行前失败并指出模块和未知引用

### Requirement: 动作顺序与失败传播
对每个模块，计划中的动作顺序 SHALL 固定为 install → config → doctor，并只包含请求且模块具备的动作。默认执行 SHALL 在首个失败时停止调度新动作；同模块后续动作和所有传递依赖方 SHALL 被标记 blocked 且不得执行。继续执行无依赖动作只能通过显式控制选项启用，且不得绕过依赖阻断。

#### Scenario: 完整生命周期计划
- **WHEN** 用户对具备三种能力的模块请求 `-icd`
- **THEN** 计划 SHALL 按 install、config、doctor 排列

#### Scenario: 安装失败
- **WHEN** install 动作执行失败
- **THEN** 同一模块的 config 和 doctor SHALL 被记录为 blocked 且不得执行
- **THEN** 进程 SHALL 以非零退出

#### Scenario: 依赖模块失败
- **WHEN** 模块 B 失败且模块 A 直接或传递依赖 B
- **THEN** A 的计划动作 SHALL 被记录为 blocked 且不得执行

#### Scenario: 显式继续执行
- **WHEN** 用户启用 continue-on-error 且后续模块不依赖失败模块
- **THEN** 后续独立模块 MAY 执行
- **THEN** 最终进程仍 SHALL 非零退出并报告失败与 blocked 动作

### Requirement: Dry-run 与显式非交互执行
系统 SHALL 支持 `--dry-run` 展示完整计划且不执行动作，并支持 `--yes` 跳过交互确认。`--yes` SHALL NOT 跳过计划校验、OS 过滤、配置备份或错误处理。

#### Scenario: Dry-run
- **WHEN** 用户对有效请求传入 `--dry-run`
- **THEN** 系统 SHALL 展示将执行的模块、动作和顺序
- **THEN** SHALL NOT 修改系统或用户文件

#### Scenario: 显式自动确认
- **WHEN** 用户对有效请求传入 `--yes`
- **THEN** 系统 SHALL 在计划校验成功后无需逐项确认执行
- **THEN** 需要替换普通配置文件时仍 SHALL 先备份

#### Scenario: 非 TTY 缺少控制旗标
- **WHEN** 命令需要确认、标准输入不是 TTY 且未传 `--yes` 或 `--dry-run`
- **THEN** 系统 SHALL 快速失败并提示使用显式控制旗标

### Requirement: 计划与执行使用一致 OS
非 dry-run 执行 SHALL 使用经检测并验证的实际 OS。显式请求与实际 OS 不一致时 SHALL 在执行前失败；跨 OS override SHALL 仅允许生成或展示计划。handler 可见的 OS 值 SHALL 与计划一致且不可在动作内重新选择另一分支。

#### Scenario: 跨 OS dry-run
- **WHEN** 用户在 Linux 上以 dry-run 请求 Darwin 计划
- **THEN** 系统 MAY 展示 Darwin 计划
- **THEN** SHALL NOT 执行 handler

#### Scenario: 跨 OS 实际执行
- **WHEN** 用户在 Linux 上请求执行 Darwin 计划
- **THEN** 系统 SHALL 在任何动作前失败并说明 OS 不一致
