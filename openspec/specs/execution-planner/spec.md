# execution-planner Specification

## Purpose
TBD - created by archiving change overhaul-dotfiles-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: 所有入口共享执行计划
系统 SHALL 使用同一 planner 为 `init`、全量动作、交互选择和显式模块动作生成执行计划。计划 SHALL 在执行前完成模块、能力、OS 适用性、profile 和依赖校验。

#### Scenario: 不同入口选择同一模块集合
- **WHEN** 两个入口在相同 OS、profile、模块和动作输入下生成计划
- **THEN** 两个计划 SHALL 包含相同且顺序一致的动作

#### Scenario: 计划校验失败
- **WHEN** 输入包含未知模块、无效 profile 或不支持的动作能力
- **THEN** planner SHALL 在执行任何动作前以非零结果失败

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
对每个模块，计划中的动作顺序 SHALL 固定为 install → config → doctor，并只包含请求且模块具备的动作。执行时前序动作失败 SHALL 阻止该模块后续动作；默认 SHALL 停止后续模块。

#### Scenario: 完整生命周期计划
- **WHEN** 用户对具备三种能力的模块请求 `-icd`
- **THEN** 计划 SHALL 按 install、config、doctor 排列

#### Scenario: 安装失败
- **WHEN** install 动作执行失败
- **THEN** 同一模块的 config 和 doctor SHALL NOT 执行
- **THEN** 进程 SHALL 以非零退出

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
