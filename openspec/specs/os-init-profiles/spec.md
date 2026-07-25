# os-init-profiles Specification

## Purpose
定义按操作系统分发的初始化入口与默认全量策略：自动检测 OS、强制指定 OS、`init` 默认覆盖该 OS 的系统包 + 适用模块的 install + config，并与全局 `-a` 入口保持职责分离。

## Requirements

### Requirement: 分系统 init 入口
系统 SHALL 提供 `dotf init` 初始化入口。未指定 OS 时 SHALL 自动检测当前系统；`--os <id>` SHALL 可显式覆盖平台选择。OS 选择 SHALL 只决定系统基础步骤和模块适用性，不得同时承担使用场景模块集合的含义。系统 SHALL 支持独立的 `--profile <name>` 选择使用场景，并支持列出平台与使用场景 profile。

#### Scenario: 自动检测
- **WHEN** 用户运行 `dotf init` 且未传 `--os`
- **THEN** 系统 SHALL 检测当前 OS 并用于适用性过滤

#### Scenario: 强制 OS
- **WHEN** 用户运行 `dotf init --os darwin`
- **THEN** planner SHALL 使用 darwin 平台规则

#### Scenario: 指定使用场景
- **WHEN** 用户运行 `dotf init --profile remote`
- **THEN** planner SHALL 选择 remote 模块集合并按当前 OS 过滤

#### Scenario: 列出 profile
- **WHEN** 用户运行 init 的列表选项
- **THEN** 输出 SHALL 区分支持的平台 ID 与使用场景 profile

### Requirement: profile 默认全量力度
未指定使用场景 profile 时，`dotf init` SHALL 使用文档声明的默认 profile。`full` profile SHALL 包含该 OS 的系统基础步骤、所有适用 install 模块和所有适用 config 模块；其它 profile SHALL 只包含其声明模块及递归依赖。所有 profile 均 SHALL 通过统一 planner 生成计划并遵循默认确认、`--dry-run` 与 `--yes` 规则。

#### Scenario: Full profile
- **WHEN** 用户运行 `dotf init --profile full`
- **THEN** 计划 SHALL 包含当前平台系统步骤及所有适用 install/config 模块

#### Scenario: 非全量 profile
- **WHEN** 用户运行 `dotf init --profile minimal`
- **THEN** 计划 SHALL 仅包含 minimal 声明模块及依赖
- **THEN** SHALL NOT 因 init 入口而自动扩展成全量模块

#### Scenario: Linux 跳过仅 macOS 模块
- **WHEN** 在 Linux 上生成任一使用场景 profile 的计划
- **THEN** 仅 darwin 适用模块 SHALL NOT 被纳入执行计划

#### Scenario: 包含系统步骤与双全集
- **WHEN** 用户确认执行某 OS 的 init
- **THEN** 流程 SHALL 包含系统包步骤、该 OS 全部可安装模块、该 OS 全部可配置模块

#### Scenario: init 不逐模块确认
- **WHEN** 用户运行 `dotf init`、通过计划确认且未传 `--yes`
- **THEN** 系统 SHALL NOT 对每个适用模块再询问「是否安装/配置」
- **THEN** 若触发更改默认 shell 或 Docker 步骤，SHALL 进行可见的副作用确认

### Requirement: 全局全量与 init 区分
`dotf -i -a` / `dotf -c -a` / `dotf -a` SHALL 继续作为全局全量入口保留。全量安装/配置在枚举模块时 SHALL 按当前 OS 过滤不适用项，与 init 的 OS 适用性规则一致。`dotf -a` SHALL NOT 自动执行系统包分发步骤（该步骤专属 `init` / `system` 模块）。

#### Scenario: -a 不含 system 包分发
- **WHEN** 用户运行 `dotf -a`
- **THEN** 执行当前 OS 适用的全部 install 与全部 config
- **THEN** SHALL NOT 隐含执行完整 `dispatch_init` 系统包流程（除非 `system` 本身作为 install 模块被包含且用户确认）

### Requirement: 内置使用场景 profile
系统 SHALL 至少提供 `minimal`、`remote`、`desktop` 和 `full` profile。profile MAY 通过 `includes` 复用其它 profile，但 SHALL 检测未知引用与包含环。

#### Scenario: Remote profile 复用 minimal
- **WHEN** remote profile includes minimal
- **THEN** remote 计划 SHALL 包含 minimal 模块、remote 自身模块及所有依赖且去重

#### Scenario: Profile 包含环
- **WHEN** profile A includes B 且 B 直接或间接 includes A
- **THEN** 校验 SHALL 失败并指出包含环

### Requirement: 本地覆盖不得进入公开 profile
公开 profile SHALL 只包含可公开复用的模块名和非私密元数据。设备专属选择或路径覆盖 SHALL 使用被 gitignore 的本地配置，且不得包含于仓库默认 profile。

#### Scenario: 设备专属覆盖
- **WHEN** 用户需要为单台设备调整 profile
- **THEN** SHALL 可通过本地覆盖完成
- **THEN** 默认公开配置 SHALL 不包含该设备的私密值