# agents-skills-install Specification

## Purpose
TBD - created by archiving change unified-agent-skills. Update Purpose after archive.
## Requirements
### Requirement: 配置工具时安装适配后的 skills/commands

当用户通过现有配置入口安装 Claude Code、Cursor、OpenCode 或 Codex 时，系统 SHALL 读取共享源、执行对应适配，并将结果安装到该工具的用户级配置位置（home 真实目录下的约定子目录）。

#### Scenario: 配置 Claude 时安装到 ~/.claude

- **WHEN** 用户执行 `dotf claude -c` 或等价调用 `config.sh claude`
- **THEN** 系统 SHALL 将启用的 skills 安装到 `~/.claude/skills/`
- **THEN** 系统 SHALL 将启用的 commands 安装到 `~/.claude/commands/` 下适配后的路径

#### Scenario: 配置 Cursor 时安装到 ~/.cursor

- **WHEN** 用户执行 `dotf cursor -c` 或等价调用
- **THEN** 系统 SHALL 将启用的 skills/commands 安装到 `~/.cursor/skills/` 与 `~/.cursor/commands/`

#### Scenario: 配置 OpenCode 时安装到 ~/.config/opencode

- **WHEN** 用户执行 `dotf opencode -c` 或等价调用，并随后（或一并）运行 agents sync
- **THEN** 系统 SHALL 将启用的 skills 安装到 `~/.config/opencode/skills/`
- **THEN** 系统 SHALL 将启用的 commands 安装到 `~/.config/opencode/commands/`
- **THEN** `~/.config/opencode` SHALL 为真实目录，SHALL NOT 整目录软链到仓库 `agents/vendors/opencode`

#### Scenario: 配置 Codex 时安装 skills

- **WHEN** 用户执行 `dotf codex -c` 或等价调用
- **THEN** 系统 SHALL 将启用的 skills 安装到 `~/.codex/skills/`
- **THEN** 若实现包含 commands→prompts 映射，则对应文件 SHALL 安装到约定的 `~/.codex/prompts/`（或文档声明的路径）

### Requirement: 安装行为安全且可重复
skills/commands runtime bundle 安装 SHALL 记录本系统拥有的目标、来源、内容 hash 和版本。对等价受管内容 SHALL 返回 unchanged；对删除的来源 SHALL 执行安全 reconcile；对用户修改或非托管同名目标 SHALL 报告 conflict，除非用户显式选择备份后替换。

#### Scenario: 重复配置幂等
- **WHEN** 用户连续两次同步且共享源、选择范围和目标内容未变
- **THEN** 第二次 SHALL 返回 unchanged
- **THEN** SHALL NOT 创建备份或重写目标

#### Scenario: 已撤销的受管 sidecar
- **WHEN** 上次 manifest 中的 sidecar 已从源 runtime bundle 删除且目标仍等于上次受管 hash
- **THEN** reconcile SHALL 删除该 stale 目标
- **THEN** SHALL 更新 managed manifest

#### Scenario: 已撤销目标被用户修改
- **WHEN** stale 目标内容不等于上次受管 hash
- **THEN** reconcile SHALL 报告 conflict
- **THEN** SHALL NOT 静默删除或覆盖该目标

#### Scenario: 冲突的非托管文件先备份
- **WHEN** 计划目标已存在但没有受管 ownership 或内容不等价
- **THEN** 默认 apply SHALL 报告 conflict 并保持目标不变
- **THEN** 显式替换时 SHALL 先创建不跟随软链的安全备份

### Requirement: 同步入口可独立调用

系统 SHALL 提供不依赖「整包工具配置」也能触发的同步入口（例如 `scripts/.../sync.sh <tool>` 或 `config.sh` 可识别的 `agents` 模块），以便只更新 skills/commands。

#### Scenario: 仅同步某一工具的 agents 内容

- **WHEN** 用户调用独立同步入口并指定 `cursor`
- **THEN** 系统 SHALL 只适配并安装 Cursor 的 skills/commands
- **THEN** SHALL NOT 要求同时重装 Cursor 的 MCP 或其他无关配置（除非该入口被实现为完整 `cursor` 配置的一部分且用户显式选择了完整配置）

#### Scenario: 同步全部目标工具

- **WHEN** 用户调用同步入口且指定全部目标工具（或等价 `agents` 全量模式）
- **THEN** 系统 SHALL 依次处理 claude、cursor、opencode、codex、kimi-code、pi（跳过清单中排除的组合）

### Requirement: Runtime bundle 与 authoring source 分离
安装到用户级 Agent 目录的 runtime bundle SHALL 只包含清单声明的运行文件。`patches`、`evals`、`experience`、`evolutions` 和其它 authoring 数据 SHALL 默认留在仓库源，不得通过源码目录软链暴露为运行时安装。

#### Scenario: 同步一手 skill
- **WHEN** skill 清单将 `SKILL.md`、`references/` 和 `scripts/` 声明为 runtime 文件
- **THEN** sync SHALL 安装这些文件并记录 hash
- **THEN** 未声明的 authoring 目录 SHALL NOT 出现在安装目标

### Requirement: 第三方 skill 可复现且可审计
默认第三方 skill SHALL 由锁定来源、不可变 revision、内容 hash 和审计元数据描述。普通 sync SHALL NOT 从浮动上游直接安装未锁定内容。

#### Scenario: 锁定第三方 skill 安装
- **WHEN** sync 安装第三方 skill
- **THEN** 获取内容 SHALL 与 lock 中的 revision 和 hash 一致
- **THEN** 不一致或审计未通过时 SHALL 在写入目标前失败
