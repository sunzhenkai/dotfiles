# module-lifecycle Specification

## Purpose
TBD - created by archiving change overhaul-dotfiles-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: 约定式模块动作处理器
系统 SHALL 从 `scripts/modules/<name>/<action>.sh` 约定位置发现 install、config、doctor 处理器，并延迟加载当前计划需要的处理器。注册表 SHALL 只声明能力和元数据，不得保存函数名、脚本路径或任意执行命令。

#### Scenario: 加载单个安装处理器
- **WHEN** 计划仅包含模块 `sdk` 的 install 动作
- **THEN** runner SHALL 只加载该模块的 install 处理器及其公共库

#### Scenario: 声明与处理器不一致
- **WHEN** 模块声明 install 能力但缺少对应处理器
- **THEN** 注册表或运行前校验 SHALL 以非零结果失败并指出模块

#### Scenario: 未声明的处理器
- **WHEN** 模块目录存在 config 处理器但注册表未声明 config 能力
- **THEN** 校验 SHALL 报告不一致且不得隐式开放该能力

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
