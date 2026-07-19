# module-registry Specification

## Purpose
维护单一模块注册表，作为 install/config/doctor 能力、路径与 OS 适用性的真相源，供 CLI 与调度只读查询。
## Requirements

### Requirement: 统一模块注册表
系统 SHALL 维护单一模块注册表作为 install/config/doctor 能力与路径的真相源。每个模块条目 SHALL 包含唯一 `name`，并可选声明 `install` 能力、`config` 能力（含仓库源路径与安装目标路径）、`doctor` 能力，以及可选的 OS 适用性。工具型模块（非 `system`/`homebrew`/`fonts`，且具备 install 和/或 config）SHALL 声明 `doctor: true`。模块 MAY 声明可选 `bin` 字段供 L0 doctor 检查 PATH。

#### Scenario: 双能力模块可查询
- **WHEN** 查询模块 `agents`
- **THEN** 注册表 SHALL 同时提供 install 与 config 能力描述

#### Scenario: 工具型模块具备 doctor
- **WHEN** 查询模块 `agents` 或 `nvim` 或 `sdk`
- **THEN** 注册表 SHALL 声明 doctor 能力为 true

#### Scenario: 仅配置模块无 install
- **WHEN** 查询模块 `nvim`
- **THEN** 注册表 SHALL 提供 config 能力
- **THEN** 注册表 SHALL NOT 声明 install 能力

#### Scenario: 仅安装模块无 config
- **WHEN** 查询模块 `sdk`
- **THEN** 注册表 SHALL 提供 install 能力
- **THEN** 注册表 SHALL NOT 声明 config 能力

#### Scenario: 非工具型可不声明 doctor
- **WHEN** 查询模块 `system`
- **THEN** 注册表可不声明 doctor 能力
- **THEN** 校验 SHALL NOT 因此失败

### Requirement: 调度只读注册表
`dotf` 及 install/config/doctor 调度逻辑 SHALL 以注册表判定模块是否存在、具备何种能力、配置源/目标路径；SHALL NOT 再维护与注册表并行的第二套模块清单作为真相源。

#### Scenario: 未知模块
- **WHEN** 用户对未注册名称请求 `-i`、`-c` 或 `-d`
- **THEN** 系统以非零退出码失败并提示可用模块

#### Scenario: 能力缺失报错
- **WHEN** 用户对仅有 config 能力的模块请求 `-i`
- **THEN** 系统以非零退出码失败并说明该模块无安装步骤
- **WHEN** 用户对仅有 install 能力的模块请求 `-c`
- **THEN** 系统以非零退出码失败并说明该模块无配置步骤
- **WHEN** 用户对未声明 doctor 的模块请求 `-d`
- **THEN** 系统以非零退出码失败并说明该模块无诊断步骤

### Requirement: OS 适用性过滤
注册表可为模块声明适用操作系统集合；未声明时 SHALL 视为全平台适用。按 OS 过滤的操作（含 `dotf init` 与全量 `-a` / `-d -a`）SHALL 只包含当前（或指定）OS 适用的模块。

#### Scenario: 过滤不适用模块
- **WHEN** 当前 OS 为 Linux 且某模块仅适用于 darwin
- **THEN** 该模块 SHALL NOT 出现在该次 OS 过滤后的 install/config/doctor 全集中

### Requirement: doctor 能力可查询
注册表 API SHALL 支持按 `doctor` 能力列出/判定模块，供 `dotf` 交互选择与全量 `-d -a` 使用。

#### Scenario: 列出可诊断模块
- **WHEN** 请求列出具备 doctor 能力的模块
- **THEN** 返回结果 SHALL 包含所有 `doctor: true` 的模块
- **THEN** 返回结果 SHALL NOT 包含未声明 doctor 的非工具型模块（如未声明时的 `system`）
