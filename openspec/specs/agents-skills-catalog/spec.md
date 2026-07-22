# agents-skills-catalog Specification

## Purpose
TBD - created by archiving change unified-agent-skills. Update Purpose after archive.
## Requirements
### Requirement: 共享源目录作为 skills/commands 唯一真相源

仓库 SHALL 提供共享目录 `agents/`，作为跨工具复用的 skills 与 commands 的唯一手写真相源。工具专属运行时文件（MCP、settings、model 配置等）MUST NOT 放入该目录作为真相源。

#### Scenario: 共享目录结构存在

- **WHEN** 仓库完成本能力落地
- **THEN** 存在 `agents/skills/<skill-id>/SKILL.md` 用于 skill 源
- **THEN** 存在 `agents/commands/<command-id>.md` 用于 command 源

#### Scenario: 新增 skill 只改共享源

- **WHEN** 维护者新增一个跨工具 skill
- **THEN** 仅需在 `agents/skills/<skill-id>/` 下新增源文件（及可选清单声明）
- **THEN** MUST NOT 要求再手写四份工具目录下的完整副本作为真相源

### Requirement: 源文件元数据约定

每个共享 skill/command 源文件 SHALL 使用 YAML frontmatter，至少包含稳定标识与描述；正文 SHALL 不绑定某一工具的路径布局。

#### Scenario: skill 源最小元数据

- **WHEN** 读取 `agents/skills/<skill-id>/SKILL.md`
- **THEN** frontmatter SHALL 包含可用于适配的 `name` 或与目录名一致的 `id`，以及 `description`
- **THEN** 正文主体 SHALL 为 Markdown，且工具相关 slash 命令引用 SHALL 使用约定占位符或由适配层改写，而非写死单一工具语法作为唯一形式

#### Scenario: command 源使用稳定 command-id

- **WHEN** 读取 `agents/commands/<command-id>.md`
- **THEN** 文件名中的 `<command-id>` SHALL 为 kebab-case 稳定 ID（例如 `opsx-propose`）
- **THEN** 该 ID SHALL 作为各工具路径映射的输入键

### Requirement: 可选的工具启用范围

系统 SHALL 支持声明某个 skill/command 对哪些工具生效（默认全部目标工具：claude、cursor、opencode、codex、kimi-code、pi），以便排除不适用的条目。

#### Scenario: 默认对全部目标工具启用

- **WHEN** 某 skill/command 未声明排除列表
- **THEN** 适配安装流程 SHALL 将其视为对全部目标工具启用

#### Scenario: 排除某一工具

- **WHEN** 某 skill/command 声明排除 `codex`
- **THEN** 针对 `codex` 的适配/安装 SHALL NOT 安装该条目
- **THEN** 其余未排除工具仍 SHALL 安装该条目

