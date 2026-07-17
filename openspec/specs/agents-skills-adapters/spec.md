# agents-skills-adapters Specification

## Purpose
TBD - created by archiving change unified-agent-skills. Update Purpose after archive.
## Requirements
### Requirement: 按工具适配 frontmatter 与路径布局

系统 SHALL 为 Claude Code、Cursor、OpenCode、Codex 各提供适配逻辑，将 `agents/` 源内容转换为该工具要求的 frontmatter 字段集合，以及 skills/commands（或 prompts）的目标相对路径。

#### Scenario: Claude command 路径嵌套

- **WHEN** 适配 command-id `opsx-propose` 到 Claude Code
- **THEN** 输出路径 SHALL 为 `commands/opsx/propose.md`（或等价嵌套布局）
- **THEN** frontmatter SHALL 包含 Claude 所用的 `name`、`description`，并 MAY 包含 `category`/`tags`

#### Scenario: Cursor command 路径扁平

- **WHEN** 适配 command-id `opsx-propose` 到 Cursor
- **THEN** 输出路径 SHALL 为 `commands/opsx-propose.md`
- **THEN** frontmatter SHALL 包含 Cursor 所用的 `name`（含 `/` 前缀形式）、`id`、`description`

#### Scenario: OpenCode command 精简 frontmatter

- **WHEN** 适配同一 command 到 OpenCode
- **THEN** 输出路径 SHALL 为 `commands/opsx-propose.md`（相对于 OpenCode 配置树）
- **THEN** frontmatter SHALL 至少包含 `description`

#### Scenario: Skill 目录名跨工具一致

- **WHEN** 适配 skill-id `openspec-propose` 到任一目标工具
- **THEN** 输出 SHALL 为 `skills/openspec-propose/SKILL.md`（Codex 同为 skills 树下该布局）

### Requirement: 正文中的工具相关引用可改写

适配层 SHALL 将源正文中的约定占位符（或等价改写规则）替换为当前工具的 slash 命令/引用写法，避免四工具共用一份写死语法。

#### Scenario: slash 命令占位符替换

- **WHEN** 源正文包含指向 `opsx-apply` 的约定占位符
- **THEN** Claude 适配结果 SHALL 使用该工具惯用写法（例如 `/opsx:apply`）
- **THEN** Cursor 与 OpenCode 适配结果 SHALL 使用其惯用写法（例如 `/opsx-apply`）

#### Scenario: 适配结果无残留占位符

- **WHEN** 某一工具的适配成功完成
- **THEN** 输出文件正文 SHALL NOT 包含未替换的 `{{...}}` 占位符标记

### Requirement: Codex 对 skills 的适配为必须，commands 映射可降级

系统 SHALL 为 Codex 适配并产出 skills。若 Codex 侧无稳定的 commands 目录约定，则 command 源 MAY 映射到 `prompts/`，且该映射行为 SHALL 在实现与文档中明确；不得因 prompts 映射不确定而跳过 skills 适配。

#### Scenario: Codex skills 适配

- **WHEN** 对 `codex` 执行适配且存在启用的 skill 源
- **THEN** 系统 SHALL 生成 `skills/<skill-id>/SKILL.md` 形式的输出

#### Scenario: Codex commands 无稳定约定时

- **WHEN** 实现时确认 Codex 无与其它工具对等的 commands 布局
- **THEN** 系统 SHALL 将 command 源映射到文档约定的降级目标（如 `prompts/<command-id>.md`），或在清单中排除 Codex 的 commands
- **THEN** skills 适配 SHALL 仍正常执行

