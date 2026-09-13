# agents-desired-set Specification

## Purpose
定义本机 Skill 的 Desired Set：它如何组成、如何经 overlay 持久化，以及 apply / remove 如何与 sync prune 绑在同一次计划里。
## Requirements
### Requirement: Desired Set 组成
本机 Desired Set SHALL 为：一手 catalog ∪ 默认选中的第三方 Skill ∪ overlay 显式启用的 Locked Skill，再减去 overlay 停用项。未锁定第三方 SHALL NOT 进入 Desired Set。OpenSpec 生成的 skill SHALL NOT 进入 Desired Set。未写 overlay 时 SHALL 保持现有默认（catalog 与默认选中项全量 sync）。

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
Skill 的 apply SHALL 在同一次计划中写入 Desired Set 并 sync，使对应制品存在。remove SHALL 在同一次计划中移出 Desired Set 并 prune owned 且未漂的目标。系统 SHALL NOT 提供只改 HOME 文件、不写 overlay 的半截操作。Conflict 目标 SHALL 留下并报告。

#### Scenario: remove 后 sync 不会装回
- **WHEN** 用户 remove 一条 Skill 且计划成功
- **THEN** overlay SHALL 记录该 Skill 停用
- **THEN** owned 且 hash 未漂的目标 SHALL 被 prune
- **THEN** 随后 `dotf agents -c` SHALL NOT 再安装该 Skill

#### Scenario: 只抠文件不算成功
- **WHEN** 目标文件已被手工删除但 overlay 仍期望该 Skill
- **THEN** 下一次 sync SHALL 按 Desired Set 重新安装或报告缺失
- **THEN** 系统 SHALL NOT 把这次手工删除当作 remove 成功

#### Scenario: Conflict 不 prune
- **WHEN** remove 的目标内容不等于上次受管 hash
- **THEN** 计划 SHALL 将其标为 Conflict
- **THEN** 默认 apply SHALL 不删除该目标
- **THEN** overlay 仍 SHALL 记录停用，以免下次把 Conflict 当未修改覆盖

