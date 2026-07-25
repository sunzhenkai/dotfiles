# plan-confirm Specification

## Purpose
TBD - created by archiving change fix-plan-confirm-ux. Update Purpose after archive.
## Requirements
### Requirement: 分层确认模型
经计划执行路径（`run_plan` / 等价 orchestrator）时，用户确认 SHALL 分为两层：
1. **计划确认**：执行前展示计划后询问是否按计划执行；默认 N；通过后授权执行计划中列出的 install/config/doctor 动作。
2. **副作用确认**：仅当步骤的副作用无法从计划行充分表达时询问；本变更最小白名单为「更改默认 shell」与「安装或配置 Docker」；默认 N。

计划确认通过 SHALL NOT 自动设置 `DOTF_YES` / `ASSUME_YES`。常规「是否安装/配置某模块」类确认在计划路径下 SHALL NOT 出现。计划中已包含 `install system` 时，「是否安装系统软件包」类确认 SHALL NOT 再出现。

#### Scenario: 计划确认后执行常规模块
- **WHEN** 用户对含 `install grepom` 与 `config k9s` 的有效计划回答计划确认为 y，且未传 `--yes`
- **THEN** 系统 SHALL 执行这些动作
- **THEN** SHALL NOT 再提示「是否安装 grepom」或「是否配置 k9s」类确认

#### Scenario: system 装包已由计划授权
- **WHEN** 计划包含 `install system` 且用户已通过计划确认、未传 `--yes`
- **THEN** 系统 SHALL NOT 再提示「是否安装系统软件包」
- **THEN** 在将更改默认 shell 或安装/配置 Docker 前 SHALL 进行副作用确认（提示对用户可见）

#### Scenario: 计划确认不等于 --yes
- **WHEN** 用户仅通过计划确认（未传 `--yes`）且将触发 Docker 副作用确认
- **THEN** 系统 SHALL 等待用户对副作用确认的显式 y/Y
- **THEN** 用户直接回车或输入非 y/Y SHALL 跳过该副作用步骤（默认 N）

### Requirement: 确认提示使用 TTY
所有面向用户的确认提示与对应输入读取 SHALL 使用 `/dev/tty`（或等价直接终端设备），SHALL NOT 依赖已被 runner 捕获的 stdout/stderr 来展示提示。当 `DOTF_YES=1` 或 `ASSUME_YES=1` 时，确认函数 SHALL 不再等待输入并视为已确认。

#### Scenario: 捕获输出时副作用确认仍可见
- **WHEN** 处理器 stdout/stderr 被 runner 重定向捕获，且需要副作用确认
- **THEN** 用户 SHALL 能在终端看到确认提示并完成输入

#### Scenario: --yes 跳过全部确认
- **WHEN** 用户对有效请求传入 `--yes`
- **THEN** 系统 SHALL 跳过计划确认与副作用确认
- **THEN** SHALL NOT 跳过计划校验、OS 过滤、配置备份或错误处理

### Requirement: 非 TTY 须显式控制旗标
当需要确认、无法使用 `/dev/tty`、且未传 `--yes` 或 `--dry-run` 时，系统 SHALL 快速失败并提示使用显式控制旗标。

#### Scenario: 管道环境缺少旗标
- **WHEN** 命令需要确认、无法读写 `/dev/tty` 且未传 `--yes` 或 `--dry-run`
- **THEN** 系统 SHALL 以非零退出并提示使用 `--yes` 或 `--dry-run`
