# agent-skills-install Specification

## Purpose
TBD - created by archiving change unified-agent-skills. Update Purpose after archive.
## Requirements
### Requirement: 配置工具时安装适配后的 skills/commands

当用户通过现有配置入口安装 Claude Code、Cursor、OpenCode 或 Codex 时，系统 SHALL 读取共享源、执行对应适配，并将结果安装到该工具的用户级配置位置（或 OpenCode 所 symlink 的仓库配置树中约定子目录）。

#### Scenario: 配置 Claude 时安装到 ~/.claude

- **WHEN** 用户执行 `dotf -c claude` 或等价调用 `config.sh claude`
- **THEN** 系统 SHALL 将启用的 skills 安装到 `~/.claude/skills/`
- **THEN** 系统 SHALL 将启用的 commands 安装到 `~/.claude/commands/` 下适配后的路径

#### Scenario: 配置 Cursor 时安装到 ~/.cursor

- **WHEN** 用户执行 `dotf -c cursor` 或等价调用
- **THEN** 系统 SHALL 将启用的 skills/commands 安装到 `~/.cursor/skills/` 与 `~/.cursor/commands/`

#### Scenario: 配置 OpenCode 时 skills/commands 对用户可见

- **WHEN** 用户执行 `dotf -c opencode` 或等价调用
- **THEN** 适配后的 skills/commands SHALL 出现在 OpenCode 实际加载的配置树中（`~/.config/opencode` 或其 symlink 目标下的 `skills/`、`commands/`）

#### Scenario: 配置 Codex 时安装 skills

- **WHEN** 用户执行 `dotf -c codex` 或等价调用
- **THEN** 系统 SHALL 将启用的 skills 安装到 `~/.codex/skills/`
- **THEN** 若实现包含 commands→prompts 映射，则对应文件 SHALL 安装到约定的 `~/.codex/prompts/`（或文档声明的路径）

### Requirement: 安装行为安全且可重复

skills/commands 安装 SHALL 可重复执行；对已由本系统管理且内容未变的目标 SHALL 可跳过；与现有备份策略一致，避免静默销毁用户手改内容而不留痕迹。

#### Scenario: 重复配置幂等

- **WHEN** 用户连续两次执行同一工具的配置且共享源未变
- **THEN** 第二次执行 SHALL 成功完成
- **THEN** 用户级目标中的托管条目内容 SHALL 与适配结果一致

#### Scenario: 冲突的非托管文件先备份

- **WHEN** 目标路径已存在且不是本系统将写入的等效托管内容（例如用户手改的同名 skill）
- **THEN** 系统 SHALL 在覆盖前将现有文件/目录备份到 `~/.config/backups/`（或仓库既有备份目录约定）
- **THEN** 再写入适配结果

### Requirement: 同步入口可独立调用

系统 SHALL 提供不依赖「整包工具配置」也能触发的同步入口（例如 `scripts/.../sync.sh <tool>` 或 `config.sh` 可识别的 `agents` 模块），以便只更新 skills/commands。

#### Scenario: 仅同步某一工具的 agents 内容

- **WHEN** 用户调用独立同步入口并指定 `cursor`
- **THEN** 系统 SHALL 只适配并安装 Cursor 的 skills/commands
- **THEN** SHALL NOT 要求同时重装 Cursor 的 MCP 或其他无关配置（除非该入口被实现为完整 `cursor` 配置的一部分且用户显式选择了完整配置）

#### Scenario: 同步全部目标工具

- **WHEN** 用户调用同步入口且指定全部目标工具（或等价 `agents` 全量模式）
- **THEN** 系统 SHALL 依次处理 claude、cursor、opencode、codex（跳过清单中排除的组合）

