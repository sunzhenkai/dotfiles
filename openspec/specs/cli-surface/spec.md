# cli-surface Specification

## Purpose

定义 dotf 用户面命令的横切对外契约：shim 分发、全局 `--json` 输出、错误码与分级诊断、旧版逃生门与 CLI 编号点选。命令的业务语义（agents / skills / 模块动作）由各自 capability 约束，本 capability 只约束"命令面"上所有命令一致的行为。

## Requirements

### Requirement: bin/dotf 是零逻辑 shim
`bin/dotf` SHALL 只负责设置 `PYTHONPATH` 并执行 `python3 -m dotf_cli`，自身不实现任何命令逻辑、参数解析或输出格式。设置环境变量 `DOTF_LEGACY_CLI=1` 时 SHALL 转发到仓库内保留的旧 bash 脚本作为应急逃生门；该逃生门 SHALL NOT 出现在任何 help 输出或文档推荐路径中。未设置逃生门且 Python 不可用时，shim SHALL 以非零码退出并给出可读报错。

#### Scenario: 正常调用
- **WHEN** 用户运行任意 `dotf <command>`
- **THEN** 进程最终执行 `python3 -m dotf_cli` 处理该命令
- **THEN** `bin/dotf` 内不包含该命令的业务逻辑

#### Scenario: 逃生门
- **WHEN** 用户设置 `DOTF_LEGACY_CLI=1` 后运行 `dotf <command>`
- **THEN** 命令由仓库内保留的旧 bash 脚本执行
- **THEN** `dotf --help` 中不出现该逃生门的说明

#### Scenario: Python 不可用
- **WHEN** 用户运行 `dotf <command>` 且系统无可用 `python3`
- **THEN** shim 以非零码退出并在 stderr 输出可读报错

### Requirement: 全局 --json 输出契约
每个 dotf 命令 SHALL 同时支持人类可读输出与 `--json` 机器可读输出。`--json` 时 stdout SHALL 只包含一个 JSON 文档；所有诊断、告警信息 SHALL 走 stderr。JSON 字段命名 SHALL 统一为 snake_case；成功结果 SHALL 包含 `ok`、`command`、`data` 字段；错误结果 SHALL 包含 `ok: false` 与 `error: {code, message}`，可选 `chain` 字段携带 `--verbose` 时的链路详情。现有命令已输出的 `--json` 字段名 SHALL NOT 变更。

#### Scenario: JSON 模式输出单一文档
- **WHEN** 用户运行 `dotf status --json`
- **THEN** stdout 是一个合法 JSON 文档且不含其它文本
- **THEN** 任何告警信息只出现在 stderr

#### Scenario: JSON 字段稳定
- **WHEN** 用户以 `--json` 调用现有已支持 `--json` 的命令（如 `dotf status`）
- **THEN** 输出字段名与下沉前保持一致

#### Scenario: 人类模式无 JSON 泄漏
- **WHEN** 用户不带 `--json` 调用任何命令
- **THEN** stdout 为人类可读文本，不混入 JSON 文档

### Requirement: 错误码与分级输出
所有命令失败 SHALL 归类到统一错误码表：usage（参数/语法）、plan（plan 生成失败）、handler（handler 执行失败）、conflict（owned 目标被改的冲突）、env（环境不满足）、internal（未预期错误）。stderr SHALL 统一带 `[dotf]` 前缀与错误码；退出码 SHALL 与错误码一一对应。`--verbose`（或 `DOTF_VERBOSE=1`）SHALL 追加 plan/handler 调用链等诊断详情。

#### Scenario: 参数错误
- **WHEN** 用户传入非法参数或旧语法
- **THEN** 退出码对应 usage，stderr 含 `[dotf]` 前缀与 usage 错误码
- **THEN** 报错文案与守卫行为与下沉前一致

#### Scenario: verbose 链路
- **WHEN** 命令因 handler 失败退出且用户传 `--verbose`
- **THEN** stderr 追加该次执行的调用链详情（planner、handler 名等）

#### Scenario: 非 verbose 简洁
- **WHEN** 命令失败且未传 `--verbose`
- **THEN** stderr 只含一行带错误码的摘要，不含调用链

### Requirement: CLI 保留独立编号点选
当命令需要用户从列表选择且 stdin/stdout 为 tty 时，系统 SHALL 提供编号点选交互（分组列表、数字或 token 选择、空输入重刷）；非 tty 环境需要交互时 SHALL 以 env 错误码拒绝而不是挂起或静默选择。编号点选是 CLI 的独立能力，SHALL NOT 强制用户进入 TUI。

#### Scenario: tty 点选
- **WHEN** 用户在 tty 中运行需要选择的命令
- **THEN** 系统展示分组编号列表并支持数字或名字 token 选择

#### Scenario: 非 tty 拒绝
- **WHEN** 在非 tty 环境（如管道、CI）中运行需要交互的命令且未显式指定选择项
- **THEN** 系统以 env 错误码退出并说明需要 tty 或显式参数

### Requirement: 命令面行为平移
下沉后每个既有命令的语法、参数、退出行为 SHALL 与下沉前保持一致：pull / init / path / status / tui / agents / skills / retry / 模块 `-i -c -d` 及反动作。`reject_legacy_syntax` 等兼容守卫 SHALL 原样平移，旧语法触发时的报错文案与退出码不变。TUI 的对外行为 SHALL 不变。

#### Scenario: 旧语法守卫
- **WHEN** 用户使用已废弃的旧语法调用
- **THEN** 报错文案与退出码与下沉前一致

#### Scenario: 模块动作
- **WHEN** 用户运行 `dotf <module> -i` 或 `-c` 或 `-d`
- **THEN** plan 由 `src/planner.py` 生成，执行仍经 `run_plan.sh` 与模块 handler
- **THEN** 对外输出与退出码与下沉前一致
