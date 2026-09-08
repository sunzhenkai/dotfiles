# dotf-modules-state Specification

## Purpose
为模块的 install / config 事实提供持久化、可读、不可被 TUI 直接编辑的最小事实层，让管理页面在不重启管线的前提下回显状态；与现有 managed manifest 互不重叠、职责清晰。
## Requirements
### Requirement: state 文件位置与 schema

系统 SHALL 在 `${XDG_STATE_HOME:-$HOME/.local/state}/dotf/modules-state.yaml` 维护模块事实。文件不存在 SHALL 不视作错误；模块未在 state 中存在 SHALL 视为该模块 `unknown`。文件 SHALL 使用 YAML，顶层键为 `schema_version`（当前 `1`）与 `modules`（模块名 → 记录）。`schema_version` SHALL 与 overlay schema 一致地加入版本字段；缺字段的旧文件 SHALL 被读为最宽松的兼容形式并被加载器宽容处理。

#### Scenario: 文件不存在
- **WHEN** `modules-state.yaml` 在标准位置不存在
- **THEN** 读取 SHALL 返回空记录集
- **THEN** SHALL NOT 报错退出

#### Scenario: 模块不存在
- **WHEN** 状态文件中无某模块的记录
- **THEN** 该模块 SHALL 视为 `unknown`
- **THEN** TUI SHALL 显示 `unknown`，不冒充 installed / absent

### Requirement: install 字段

`modules.<name>.install` SHALL 在 install 成功（动作结果 `changed` 或 `unchanged`）后写入；`deinstall` 期间（uninstall 成功）SHALL 清空。字段 SHALL 至少包含 `last_at`（ISO8601 UTC 时间字符串）；MAY 包含 `version`（字符串）与 `path`（字符串）。无 version / path SHALL 合法。

#### Scenario: install 写字段
- **WHEN** 模块 `grepom` 的 install 动作结果为 `changed` 或 `unchanged`
- **THEN** state SHALL 新增或更新 `modules.grepom.install.last_at`
- **THEN** 若 handler 输出包含 version SHALL 写入 `install.version`

#### Scenario: uninstall 清字段
- **WHEN** 模块 `grepom` 的 uninstall 动作结果为 `changed`
- **THEN** `modules.grepom.install` SHALL 被删除
- **THEN** `modules.grepom.config` SHALL 也被删除（若存在）

### Requirement: config 字段委托给 manifest

`modules.<name>.config` SHALL 不重复存储 hash / target / mode；其 SHALL 至少包含 `last_at` 与 `manifest_managed`（managed manifest 中该模块 owner 的目标数）。该字段 SHALL 由 config / deconfig 成功动作维护；deconfig 成功后 SHALL 删除 `config` 字段。状态字段 SHALL 仅作为 manifest 的索引与时间戳引用，不当作真实备份。

#### Scenario: config 写字段
- **WHEN** 模块 `nvim` 的 config 动作结果为 `changed` 或 `unchanged`
- **THEN** state SHALL 写 `modules.nvim.config.last_at` 与 `modules.nvim.config.manifest_managed`（取自 manifest 当前 owner 数）
- **THEN** SHALL NOT 复制 manifest 的 hash / target / mode 内容

#### Scenario: deconfig 清字段
- **WHEN** 模块 `nvim` 的 deconfig 动作结果为 `changed`
- **THEN** `modules.nvim.config` SHALL 被删除
- **THEN** `modules.nvim.install` SHALL 保持不变

#### Scenario: manifest 漂移不直接改 state
- **WHEN** managed manifest 报告中某模块 `changed` / `missing`
- **THEN** state 的 `config.last_at` SHALL 不被自动刷新
- **THEN** TUI SHALL 从 manifest 直接显示漂移状态

### Requirement: 写入责任归属

state 文件 SHALL 仅由 `dotf` 自身（runner 或其 hook）在动作结果确定后写入；TUI、CLI 调用者与第三方脚本 SHALL NOT 直接修改。任何对文件的修改 SHALL 走原子写（写临时文件 + rename）。同一动作结果 SHALL 可幂等写入（重复跑 install / config 不应让 state 内容抖动）。

#### Scenario: 写文件失败不致命
- **WHEN** 写 state 临时文件失败
- **THEN** 原 runner SHALL 记录 warn 但 SHALL NOT 因写 state 失败而把动作从 `changed` 降级为 `failed`

#### Scenario: 重复 install 不抖动
- **WHEN** 用户在 1 分钟内对同一模块连续两次 install 且均 `unchanged`
- **THEN** state 的 `install.last_at` SHALL 更新为较新时间
- **THEN** SHALL NOT 出现 version / path 字段被反复清空的抖动

### Requirement: 加载器契约

加载器 SHALL 提供只读函数读取 state 并以结构化形式返回 `{installed, configured, last_at}`；不可写。加载器 SHALL 容忍缺失字段、未知字段与未知 schema_version（降级为 unknown 而非抛错）。加载器 SHALL 不主动调用 manifest / overlay / journal；调用方按需组合。

#### Scenario: 缺字段
- **WHEN** state 仅有 `modules.grepom.install.last_at`，缺 `version` / `path`
- **THEN** 加载器 SHALL 返回该模块 installed=true、version=None
- **THEN** SHALL NOT 抛错

#### Scenario: 未知 schema_version
- **WHEN** state 的 `schema_version` 大于加载器已知版本
- **THEN** 加载器 SHALL 视为整文件 unknown 并返回空记录
- **THEN** SHALL 在日志中输出 warn，但 SHALL NOT 抛错

### Requirement: 与 managed manifest / overlay 的边界

state SHALL 与 managed manifest、XDG overlay 严格不重叠：state 不存配置 hash、不存 desired set、不存 secret。TUI 状态字段 SHALL 仅在 state 字段为 `unknown` 时回退到 manifest / overlay；state 给出 `installed` / `configured` 时 SHALL 信任 state，但同时 SHALL 标注 manifest 漂移（若存在）。

#### Scenario: 三源并存不重复
- **WHEN** 模块 `nvim` 已 install 且已 config
- **THEN** state SHALL 给出 `installed=true, configured=true`
- **THEN** manifest SHALL 仍独立给出 `unchanged` / `changed`
- **THEN** TUI SHALL 同时显示 state 字段与 manifest 漂移标志

#### Scenario: 漂移标红但不降级
- **WHEN** state 说 `configured=true` 但 manifest 报告 `changed`
- **THEN** TUI SHALL 在该行展示 `configured (drift)` 样式
- **THEN** SHALL NOT 把 state 字段直接改成 `unknown`
