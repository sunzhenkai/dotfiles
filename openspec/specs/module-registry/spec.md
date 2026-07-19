## Requirements

### Requirement: 统一模块注册表
系统 SHALL 维护单一模块注册表作为 install/config 能力与路径的真相源。每个模块条目 SHALL 包含唯一 `name`，并可选声明 `install` 能力、`config` 能力（含仓库源路径与安装目标路径），以及可选的 OS 适用性。

#### Scenario: 双能力模块可查询
- **WHEN** 查询模块 `agents`
- **THEN** 注册表 SHALL 同时提供 install 与 config 能力描述

#### Scenario: 仅配置模块无 install
- **WHEN** 查询模块 `nvim`
- **THEN** 注册表 SHALL 提供 config 能力
- **THEN** 注册表 SHALL NOT 声明 install 能力

#### Scenario: 仅安装模块无 config
- **WHEN** 查询模块 `sdk`
- **THEN** 注册表 SHALL 提供 install 能力
- **THEN** 注册表 SHALL NOT 声明 config 能力

### Requirement: 调度只读注册表
`dotf` 及 install/config 调度逻辑 SHALL 以注册表判定模块是否存在、具备何种能力、配置源/目标路径；SHALL NOT 再维护与注册表并行的第二套模块清单作为真相源。

#### Scenario: 未知模块
- **WHEN** 用户对未注册名称请求 `-i` 或 `-c`
- **THEN** 系统以非零退出码失败并提示可用模块

#### Scenario: 能力缺失报错
- **WHEN** 用户对仅有 config 能力的模块请求 `-i`
- **THEN** 系统以非零退出码失败并说明该模块无安装步骤
- **WHEN** 用户对仅有 install 能力的模块请求 `-c`
- **THEN** 系统以非零退出码失败并说明该模块无配置步骤

### Requirement: OS 适用性过滤
注册表可为模块声明适用操作系统集合；未声明时 SHALL 视为全平台适用。按 OS 过滤的操作（含 `dotf init` 与建议的全量 `-a`）SHALL 只包含当前（或指定）OS 适用的模块。

#### Scenario: 过滤不适用模块
- **WHEN** 当前 OS 为 Linux 且某模块仅适用于 darwin
- **THEN** 该模块 SHALL NOT 出现在该次 OS 过滤后的 install/config 全集中
