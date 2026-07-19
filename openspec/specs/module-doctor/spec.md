# module-doctor Specification

## Purpose
为工具型模块提供一等 doctor 能力：CLI `-d` 与组合动作、L0 默认诊断、agents 深度诊断入口，以及退出码与旁路清理约定。
## Requirements

### Requirement: 工具型模块强制 doctor 能力
系统 SHALL 将注册表中除非工具型排除名单（`system`、`homebrew`、`fonts`）以外、具备 install 和/或 config 的模块视为工具型模块。每个工具型模块 SHALL 声明 `doctor: true`。校验发现工具型模块缺少该声明时 SHALL 以非零退出失败。

#### Scenario: 工具型模块具备 doctor
- **WHEN** 查询模块 `nvim` 或 `sdk` 或 `agents`
- **THEN** 注册表 SHALL 声明 `doctor: true`

#### Scenario: 非工具型不强制 doctor
- **WHEN** 查询模块 `system` 或 `homebrew` 或 `fonts`
- **THEN** 系统 SHALL NOT 因缺少 `doctor: true` 而校验失败

#### Scenario: 工具型缺少 doctor 声明
- **WHEN** 校验注册表且某工具型模块未声明 `doctor: true`
- **THEN** 校验 SHALL 以非零退出码失败并指出模块名

### Requirement: CLI 提供 -d 一等动作
系统 SHALL 支持主体优先语法下的诊断动作：`dotf <module...> -d` / `--doctor`，以及无模块时的 `dotf -d`（交互选择具备 doctor 的模块）。用户对无 doctor 能力的模块请求 `-d` 时 SHALL 非零退出并说明原因。

#### Scenario: 诊断指定模块
- **WHEN** 运行 `dotf nvim -d`
- **THEN** 系统 SHALL 对该模块执行 doctor 调度

#### Scenario: 多模块诊断
- **WHEN** 运行 `dotf nvim kitty -d`
- **THEN** 系统 SHALL 依次对 nvim、kitty 执行 doctor

#### Scenario: 无 doctor 能力报错
- **WHEN** 运行 `dotf system -d` 且 system 未声明 doctor
- **THEN** 系统以非零退出码失败并说明该模块无诊断步骤

### Requirement: 支持组合动作且顺序固定
系统 SHALL 支持组合动作 `-id`、`-cd`、`-icd` 及其分写等价（`-i -d`、`-c -d`、`-i -c -d`）。对每个模块，执行顺序 SHALL 为 install → config → doctor（仅执行动作集合中包含的步骤）。前一步骤非零退出时 SHALL 终止该模块后续步骤及后续模块。

#### Scenario: 配置后诊断
- **WHEN** 运行 `dotf agents -cd`
- **THEN** 系统 SHALL 先执行 agents config，成功后再执行 agents doctor

#### Scenario: 安装配置后诊断
- **WHEN** 运行 `dotf agents -icd`
- **THEN** 系统 SHALL 按 install → config → doctor 顺序执行

#### Scenario: 组合中前序失败终止
- **WHEN** 运行 `dotf agents -cd` 且 config 以非零退出
- **THEN** SHALL NOT 执行 agents doctor
- **THEN** 进程以非零退出码结束

#### Scenario: 分写等价于组合
- **WHEN** 运行 `dotf nvim -c -d`
- **THEN** 行为 SHALL 与 `dotf nvim -cd` 等价

### Requirement: 全量 -a 不含 doctor
`dotf -a` / `--all` SHALL 仅表示安装全部 + 配置全部（按 OS 过滤），SHALL NOT 隐式执行 doctor。全量诊断 SHALL 要求显式包含 `-d`（例如 `dotf -d -a`、`dotf -cd -a`）。

#### Scenario: 单独 -a 不跑 doctor
- **WHEN** 运行 `dotf -a` 或 `dotf --all`
- **THEN** 系统 SHALL 执行全量 install 与 config
- **THEN** SHALL NOT 执行任何模块的 doctor

#### Scenario: 显式全量诊断
- **WHEN** 运行 `dotf -d -a`
- **THEN** 系统 SHALL 对当前 OS 适用的、具备 doctor 能力的模块依次执行 doctor
- **THEN** SHALL NOT 仅因 `-a` 而执行 install 或 config（除非动作集合同时包含 i/c）

### Requirement: L0 默认诊断
对未提供专用 doctor 实现的模块，系统 SHALL 提供 L0 默认诊断：若具备 config，则检查展开后的 target 路径是否存在；若具备 install 且可判定命令名（注册表 `bin` 或合理约定），则检查命令是否在 PATH；无法判定的检查 SHALL 标记为 skip 而非 fail。OS 不适用的模块在按 OS 过滤的全集中 SHALL NOT 被执行。

#### Scenario: config 模块目标存在
- **WHEN** 对仅有 config 的模块运行 doctor 且 target 路径存在
- **THEN** doctor SHALL 报告成功（或 pass）并零退出（无其它 fail 时）

#### Scenario: config 模块目标缺失
- **WHEN** 对仅有 config 的模块运行 doctor 且 target 路径不存在
- **THEN** doctor SHALL 报告失败（或 fail）并以非零退出
- **THEN** 输出 SHALL 建议运行对应的 config 动作（如 `dotf <module> -c`）

#### Scenario: 无法判定二进制时 skip
- **WHEN** 对仅有 install 的模块运行 L0 doctor 且无法判定应检查的命令名
- **THEN** doctor SHALL 将相关检查标为 skip（或等价说明）
- **THEN** 该 skip 单独 SHALL NOT 导致非零退出

### Requirement: agents 走专用 doctor 入口
模块 `agents` 的 doctor SHALL 调用现有 agents 深度诊断实现（如 `scripts/agents/doctor.py`），而非仅 L0。诊断专用选项（如 `--json`、`--deep`、`--profile`）SHALL 在 `dotf agents -d`（及含 d 的组合）时可透传。

#### Scenario: agents -d 调用深度诊断
- **WHEN** 运行 `dotf agents -d`
- **THEN** 系统 SHALL 运行 agents 深度 doctor
- **THEN** 报告 SHALL 包含分组检查结果（env/tools/mcp/skills 等，按实现范围）

#### Scenario: 透传 json 选项
- **WHEN** 运行 `dotf agents -d --json`
- **THEN** doctor SHALL 输出机器可读 JSON（密钥红acted）

### Requirement: 退出码与宽松输出
doctor 在存在任一 fail 或执行错误时 SHALL 以非零退出；若仅有 pass/warn/skip 则 SHALL 以零退出。多检查项实现 SHOULD 使用 `pass`/`warn`/`fail`/`skip`；检查项很少的 L0 实现 MAY 使用自由文本，但 MUST 遵守上述退出码约定。

#### Scenario: 仅有警告时零退出
- **WHEN** doctor 仅产生 warn 或 skip、无 fail
- **THEN** 进程退出码 SHALL 为 0

#### Scenario: 存在失败时非零退出
- **WHEN** doctor 产生至少一个 fail
- **THEN** 进程退出码 SHALL 为非零

### Requirement: 删除 agents 配置旁路 --doctor
系统 SHALL NOT 再接受将 `--doctor` 作为 config/sync 旁路旗标（例如 `dotf agents -c --doctor`）。此类用法 SHALL 失败并提示改用 `dotf agents -d` 或 `dotf agents -cd`。

#### Scenario: 旧旁路被拒绝
- **WHEN** 运行 `dotf agents -c --doctor`
- **THEN** 系统以非零退出码失败
- **THEN** 错误信息 SHALL 提示使用 `-d` 或 `-cd`
