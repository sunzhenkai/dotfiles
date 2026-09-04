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
每次实际执行 SHALL 在 `${XDG_STATE_HOME:-$HOME/.local/state}/dotf/` 下维护带唯一 run id 的逐动作 journal，并在完成后原子更新兼容的最近执行摘要。终端、JSON、journal 和摘要 SHALL 使用同一脱敏规则；机器输出 SHALL 只包含计划版本、模块、动作、状态、耗时、时间、受限 reason code/消息和必要 hash，不得包含环境变量值、凭据、文件内容或完整命令输出。

#### Scenario: 执行开始
- **WHEN** 用户确认一个有效计划并开始执行
- **THEN** 系统 SHALL 在首个动作前创建受限权限的 run journal
- **THEN** 每个动作结束后 SHALL 记录 completed、failed、blocked 或 interrupted 状态

#### Scenario: 执行完成
- **WHEN** 一次实际计划执行结束
- **THEN** 系统 SHALL 原子更新包含成功、失败、blocked 或 interrupted 动作的最近执行摘要
- **THEN** 摘要 SHALL 指向本次 run journal

#### Scenario: 报告隐私
- **WHEN** handler reason、异常或输出包含 credential、authorization、cookie、URI userinfo、token、key 或已知敏感环境变量值
- **THEN** 终端机器输出和持久化状态 SHALL 替换或省略该值
- **THEN** SHALL 保留不含秘密的 reason code 供诊断

#### Scenario: 中断执行
- **WHEN** 进程收到可处理的中断信号
- **THEN** journal SHALL 保留已完成动作并把当前运行标记 interrupted
- **THEN** 最近执行摘要 SHALL NOT 继续指向更早且被误认为最新的运行

#### Scenario: 并发执行
- **WHEN** 两个执行尝试同时更新状态
- **THEN** 它们 SHALL 使用独立 run id 和安全锁/原子替换
- **THEN** journal 和最近摘要 SHALL NOT 被混写

### Requirement: 失败动作重试
系统 SHALL 提供 `dotf retry`，从兼容且完整的最近执行摘要选择 failed 动作，并通过与正常入口相同的 planner、严格注册表、动作能力、OS 和递归依赖校验重新生成计划。retry SHALL NOT 信任报告中的任意 module/action 字段直接构造可执行记录，也 SHALL NOT 自动追加原计划之外的新动作。

#### Scenario: 重试失败动作
- **WHEN** 最近摘要包含 failed 动作且该动作能力、OS 和递归依赖仍满足
- **THEN** planner SHALL 生成仅含该失败动作的有效 retry 计划
- **THEN** 执行器 SHALL 按正常计划校验后运行

#### Scenario: 报告包含无能力动作
- **WHEN** 最近摘要声称某模块的未声明动作失败
- **THEN** retry SHALL 在执行前拒绝该记录
- **THEN** SHALL NOT 调用 handler

#### Scenario: 无可重试报告
- **WHEN** 最近报告不存在、损坏、版本不兼容、未完成或没有 failed 动作
- **THEN** retry SHALL 不修改环境并给出明确说明

#### Scenario: 重试前依赖失效
- **WHEN** failed 动作的任一递归依赖不再满足
- **THEN** retry SHALL 在执行前失败
- **THEN** SHALL 建议用户重新运行正常计划
