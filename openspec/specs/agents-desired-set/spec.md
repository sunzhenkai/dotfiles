# agents-desired-set Specification

## Purpose
定义本机 Skill 与 MCP Entry 的 Desired Set：它如何组成、如何经 overlay 持久化，以及 apply / remove 如何与 sync prune 绑在同一次计划里。
## Requirements
### Requirement: Desired Set 组成
本机 Desired Set SHALL 为：一手 catalog ∪ 默认选中的第三方 Skill ∪ overlay 显式启用的 Locked Skill ∪ overlay 显式启用的 MCP Server，再减去 overlay 停用项。未锁定第三方 SHALL NOT 进入 Desired Set。OpenSpec 生成的 skill SHALL NOT 进入 Desired Set。未写 overlay 时 SHALL 保持现有默认（catalog 与默认选中项全量 sync；MCP 跟随当前 profile）。

#### Scenario: 默认不过滤一手 skill
- **WHEN** overlay 未声明任何 skill 停用或额外启用
- **THEN** sync SHALL 仍安装一手 catalog 与默认选中第三方
- **THEN** SHALL NOT 要求用户先写 overlay

#### Scenario: 停用后不再期望
- **WHEN** overlay 将 `grill-with-docs` 标为停用
- **THEN** Desired Set SHALL NOT 包含该 Skill
- **THEN** 随后 sync SHALL 把它视为应 prune 的 owned 目标（若 hash 未漂）

#### Scenario: 启用 lock 但不在默认列表的 skill
- **WHEN** overlay 启用一条 lock 已批准、但不在默认选中列表中的第三方 Skill
- **THEN** Desired Set SHALL 包含它
- **THEN** apply SHALL 能把它装到本机

#### Scenario: 拒绝未锁定 skill
- **WHEN** 用户对未锁定的第三方 Skill 请求 apply
- **THEN** 系统 SHALL 在写入 overlay 或目标前以非零失败
- **THEN** SHALL NOT 从浮动上游安装

### Requirement: overlay 只影响本机
Desired Set 的本机加减 SHALL 只写入 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/` 下已有 overlay 契约。apply / remove SHALL NOT 修改仓库中的 `agents/skills/`、`skills-defaults.yaml`、lock 文件或 `agents/env` 编目。

#### Scenario: remove 不改仓库
- **WHEN** 用户 remove 一条一手 Skill
- **THEN** 系统 SHALL 只更新本机 overlay 与 HOME 受管目标
- **THEN** 仓库源 SHALL 保持不变

#### Scenario: 另一台机器不受影响
- **WHEN** 机器 A 的 overlay 停用了某 Skill
- **THEN** 机器 B 在无该 overlay 时 SHALL 仍按默认 Desired Set 同步该 Skill

### Requirement: apply 与 remove 原子绑定 sync
Skill 或 MCP Entry 的 apply SHALL 在同一次计划中写入 Desired Set 并 sync，使对应制品或 Entry 存在。remove SHALL 在同一次计划中移出 Desired Set 并 prune owned 且未漂的目标。系统 SHALL NOT 提供只改 HOME 文件、不写 overlay 的半截操作。Conflict 目标 SHALL 留下并报告。

#### Scenario: remove 后 sync 不会装回
- **WHEN** 用户 remove 一条 Skill 且计划成功
- **THEN** overlay SHALL 记录该 Skill 停用
- **THEN** owned 且 hash 未漂的目标 SHALL 被 prune
- **THEN** 随后 `dotf agents -c` SHALL NOT 再安装该 Skill

#### Scenario: 只抠文件不算成功
- **WHEN** 目标文件已被手工删除但 overlay 仍期望该 Skill 或 MCP Entry
- **THEN** 下一次 sync SHALL 按 Desired Set 重新安装或报告缺失
- **THEN** 系统 SHALL NOT 把这次手工删除当作 remove 成功

#### Scenario: Conflict 不 prune
- **WHEN** remove 的目标内容不等于上次受管 hash
- **THEN** 计划 SHALL 将其标为 Conflict
- **THEN** 默认 apply SHALL 不删除该目标
- **THEN** overlay 仍 SHALL 记录停用，以免下次把 Conflict 当未修改覆盖

### Requirement: Skill 整机、MCP 默认按工具
Skill 的 apply / remove SHALL 以本机为粒度，对所有读取共享 skills 目录的工具生效；Kiro 镜像 SHALL 跟随同一 Desired Set。MCP Entry 的 apply / remove 默认针对一个目标工具的结构化配置文件中的一条记录。用户显式选择「本机全部工具」时，MCP remove SHALL 对该机所有支持 MCP 的工具生效。MCP 操作 SHALL NOT 删除整份配置文件。

#### Scenario: remove Skill 影响共享目录
- **WHEN** 用户 remove `grill-with-docs`
- **THEN** 共享 `~/.agents/skills/grill-with-docs` 在 owned 且未漂时 SHALL 被 prune
- **THEN** 读取该目录的工具 SHALL 不再看到该 Skill

#### Scenario: 默认按工具 remove MCP
- **WHEN** 用户对 Cursor 的 `web-reader` 执行 remove 且未指定全部工具
- **THEN** 系统 SHALL 从 Cursor 的结构化 MCP 配置中去掉该 Entry
- **THEN** 其他工具中的同名 Entry SHALL 保持，除非也被选中

#### Scenario: 不删除整份 mcp.json
- **WHEN** 用户 remove Cursor 上的一条 MCP Entry
- **THEN** Cursor 的 MCP 配置文件 SHALL 仍存在
- **THEN** 未选中的其它 Entry 与非托管条目 SHALL 保留
