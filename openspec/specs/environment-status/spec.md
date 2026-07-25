# environment-status Specification

## Purpose
TBD - created by archiving change overhaul-dotfiles-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: 只读环境状态
系统 SHALL 提供 `dotf status`，根据当前 OS 与所选使用场景 profile 生成期望计划并执行只读 L0 检查。该命令 SHALL NOT 安装工具、改写配置或创建备份。

#### Scenario: 查看默认环境状态
- **WHEN** 用户运行 `dotf status`
- **THEN** 系统 SHALL 展示期望模块的 install/config/doctor 可判定状态
- **THEN** SHALL NOT 修改系统或用户文件

#### Scenario: 查看指定 profile
- **WHEN** 用户运行 `dotf status --profile remote`
- **THEN** 状态范围 SHALL 仅覆盖 remote profile 及其依赖

### Requirement: 脱敏执行报告
每次实际执行 SHALL 在 `${XDG_STATE_HOME:-$HOME/.local/state}/dotf/` 下保存最近执行报告。报告 SHALL 仅包含计划版本、模块、动作、结果、耗时、时间和脱敏原因，不得包含环境变量值、凭据、文件内容或完整命令输出。

#### Scenario: 执行完成
- **WHEN** 一次计划执行结束
- **THEN** 系统 SHALL 保存包含成功与失败动作的最近执行报告

#### Scenario: 报告隐私
- **WHEN** 动作使用 API Key 或本地私密配置
- **THEN** 报告 SHALL NOT 保存对应值或文件内容

### Requirement: 失败动作重试
系统 SHALL 提供 `dotf retry`，从兼容的最近执行报告中选择 failed 动作，重新通过 planner 校验后执行。首版 retry SHALL NOT 自动追加原计划之外的新动作，依赖已不满足时 SHALL 明确失败并建议重新生成计划。

#### Scenario: 重试失败动作
- **WHEN** 最近报告包含一个 failed 动作且其依赖仍满足
- **THEN** `dotf retry` SHALL 只重新执行该失败动作

#### Scenario: 无可重试报告
- **WHEN** 最近报告不存在、版本不兼容或没有 failed 动作
- **THEN** `dotf retry` SHALL 不修改环境并给出明确说明

#### Scenario: 重试前依赖失效
- **WHEN** failed 动作的必要依赖不再满足
- **THEN** retry SHALL 在执行前失败并建议用户重新运行正常计划
