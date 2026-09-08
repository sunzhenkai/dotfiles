# dotf-tui Specification

## Purpose
提供 `dotf tui` 作为同一 planner / runner / sync 管线的交互皮肤，用来浏览模块与 Agent 制品、多选动作并提交已有计划。
## Requirements
### Requirement: 显式 TUI 入口
系统 SHALL 提供命令 `dotf tui`。该命令 SHALL 要求可用 TTY；无 TTY 时 SHALL 以非零退出并提示使用 CLI。无参数 `dotf` 与 `dotf -h` SHALL 仍显示帮助，SHALL NOT 打开 TUI。

#### Scenario: TTY 下打开 TUI
- **WHEN** 用户在 TTY 中运行 `dotf tui`
- **THEN** 系统 SHALL 打开交互界面
- **THEN** SHALL NOT 在打开时修改 HOME 或仓库

#### Scenario: 非 TTY 拒绝
- **WHEN** 用户在非 TTY 环境运行 `dotf tui`
- **THEN** 系统 SHALL 以非零退出
- **THEN** 错误 SHALL 提示改用 CLI 动词

#### Scenario: 无参数仍是帮助
- **WHEN** 用户运行 `dotf` 且无参数
- **THEN** 系统 SHALL 显示帮助
- **THEN** SHALL NOT 打开 TUI

### Requirement: 两区清单
TUI SHALL 分两区展示：Modules 区列出注册表中当前 OS 适用的模块；Agent 区列出一手 catalog、默认选中第三方、lock 已批准项以及已在 Desired Set 中的 Skill，以及编目中的 MCP Server（按工具呈现为 MCP Entry）。OpenSpec 生成的 skill SHALL NOT 出现。未声明 uninstall 的模块 SHALL 不展示 uninstall 动作。

#### Scenario: 分区展示
- **WHEN** TUI 打开
- **THEN** 用户 SHALL 能分别浏览 Modules 与 Agent 两区
- **THEN** Agent 区 SHALL 同时列出 Skill 与 MCP Entry

#### Scenario: 不可卸载不显示卸载
- **WHEN** 模块未声明 uninstall
- **THEN** 该行 SHALL NOT 提供 uninstall 动作
- **THEN** 仍可展示其具备的 config / deconfig / doctor / 状态

#### Scenario: OpenSpec skill 不列出
- **WHEN** 本机 `~/.agents/skills` 存在 `openspec-apply-change`
- **THEN** TUI Agent 区 SHALL NOT 把它列为可 apply / remove 的 Skill

### Requirement: TUI 只提交已有计划
TUI 发起的任何会改环境的操作 SHALL 生成与对应 CLI 相同的 planner 计划，并走同一套计划确认、副作用确认、journal 与 retry。TUI SHALL NOT 直接写 HOME、overlay、仓库或绕过 planner。没有对应 CLI 动词的动作 SHALL NOT 出现在 TUI。

#### Scenario: 与 CLI 计划一致
- **WHEN** 用户在 TUI 中对模块 `nvim` 选择 deconfig 并确认
- **THEN** 系统 SHALL 生成与 `dotf nvim --deconfig` 在相同 OS / profile 下等价的计划
- **THEN** 确认与执行 SHALL 复用同一 runner

#### Scenario: 无 CLI 则无按钮
- **WHEN** 某动作尚无 CLI 入口
- **THEN** TUI SHALL NOT 展示该动作

#### Scenario: 多选一份计划
- **WHEN** 用户在 TUI 中勾选多个模块或制品动作后确认
- **THEN** 系统 SHALL 生成一份完整计划并只做一次计划确认
- **THEN** SHALL NOT 对每一行单独执行且绕过计划

### Requirement: 状态只读展示
TUI SHALL 展示模块的 `dotf status` 可判定状态，以及 Skill / MCP Entry 的 doctor / sync 计划可判定状态（含 Conflict、缺失、owned、未在 Desired Set）。展示 SHALL NOT 修改环境。TUI SHALL NOT 提供名为 update 的动作；对 drifted 行 MAY 提供重新执行已有 install / config / apply 的入口。

#### Scenario: 只读刷新状态
- **WHEN** 用户在 TUI 中刷新状态
- **THEN** 系统 SHALL 只读读取 status / doctor 结果
- **THEN** SHALL NOT 安装、配置或写入 overlay

#### Scenario: 无 update 动作
- **WHEN** 某模块配置已 drifted
- **THEN** TUI MAY 提供重新 config
- **THEN** SHALL NOT 展示独立的 update 动作
