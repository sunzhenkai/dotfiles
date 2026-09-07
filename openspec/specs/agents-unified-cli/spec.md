# agents-unified-cli Specification

## Purpose
TBD - created by archiving change unify-agents. Update Purpose after archive.
## Requirements
### Requirement: Unified agents config module
The system SHALL expose a single primary config module named `agents` that synchronizes both shared skills/commands and agent environment MCP/profile configuration.

#### Scenario: User configures agents
- **WHEN** the user runs `dotf agents -c` or the equivalent config script entry
- **THEN** the system SHALL sync skills/commands for supported tools
- **THEN** the system SHALL sync MCP/profile configuration for tools that support it
- **THEN** the operation SHALL be idempotent when repeated with the same inputs

#### Scenario: Tool filter is provided
- **WHEN** the user requests sync for a specific tool such as `cursor`
- **THEN** skills and env/MCP sync SHALL be limited to that tool where applicable
- **THEN** unsupported combinations SHALL be reported as intentional skips rather than hard failures

### Requirement: Granular sync flags
The system SHALL allow users to restrict sync scope without abandoning the unified `agents` entry.

#### Scenario: Skills-only sync
- **WHEN** the user requests skills-only sync through the unified agents CLI
- **THEN** the system SHALL sync skills/commands
- **THEN** the system SHALL NOT modify MCP configuration

#### Scenario: Env-only sync
- **WHEN** the user requests env-only sync through the unified agents CLI
- **THEN** the system SHALL sync MCP/profile configuration
- **THEN** the system SHALL NOT rewrite skills/commands outputs

### Requirement: Per-tool installers use unified sync
单工具模块（Claude/Cursor/OpenCode/Codex/Kimi Code）的 install SHALL 只安装该工具 CLI，config SHALL 只应用该工具 vendor 配置。单工具 config SHALL NOT 隐式触发其它工具或共享 skills/commands/MCP 的聚合同步。共享同步 SHALL 由 `dotf agents -c` 或用户明确调用带工具过滤的统一 agents sync 入口完成。

#### Scenario: Cursor config runs
- **WHEN** 用户运行 `dotf cursor -c`
- **THEN** Cursor 特定 settings/MCP 安装 MAY 仍然执行
- **THEN** 共享 skills 与托管 MCP 同步 SHALL 走统一 agents sync 路径
- **THEN** 重复执行 SHALL 保持幂等

#### Scenario: Cursor 单工具配置
- **WHEN** 用户运行 `dotf cursor -c`
- **THEN** 系统 SHALL 只应用 Cursor vendor 配置
- **THEN** SHALL NOT 同步其它工具或隐式执行全量 agents sync

#### Scenario: 显式过滤同步
- **WHEN** 用户通过统一 agents 入口明确请求仅同步 cursor
- **THEN** 共享 skills 与托管 MCP 同步 SHALL 只覆盖 Cursor 适用目标
- **THEN** 重复执行 SHALL 保持幂等

#### Scenario: 聚合同步
- **WHEN** 用户运行 `dotf agents -c`
- **THEN** 系统 SHALL 按统一 agents 配置模块契约同步支持工具

### Requirement: Scripts expose a single agents CLI surface
The system SHALL provide scripts under `scripts/agents/` as the single CLI surface for sync and doctor orchestration, implemented as one self-contained Python package with no reverse dependency on any other agent script directory. Sync entrypoints SHALL NOT accept a `--doctor` flag; diagnosis SHALL be invoked via the module doctor action (`dotf agents -d`) or by calling the doctor script directly.

#### Scenario: User invokes scripts directly
- **WHEN** the user runs `scripts/agents/sync.sh` without going through `dotf`
- **THEN** the command SHALL support the same core scopes as `dotf agents -c`
- **THEN** documentation SHALL present this path as equivalent to the config module

#### Scenario: Sync rejects doctor flag
- **WHEN** the user runs `scripts/agents/sync.sh --doctor` or `dotf agents -c --doctor`
- **THEN** the command SHALL fail with a non-zero exit
- **THEN** the error SHALL direct the user to `dotf agents -d` or `dotf agents -cd`

#### Scenario: No parallel agent script directory
- **WHEN** the sync/doctor logic is loaded
- **THEN** all core implementation modules SHALL reside under `scripts/agents/`
- **THEN** the code SHALL NOT import agent logic from a separate `scripts/agent-env/` directory

### Requirement: Agents dual capability via subject-first CLI
The `agents` module SHALL be registered with install, config, and doctor capabilities. Users SHALL be able to run `dotf agents -i`, `dotf agents -c`, `dotf agents -d`, and combinations such as `dotf agents -ic` and `dotf agents -cd` under the subject-first CLI.

#### Scenario: Install then config
- **WHEN** the user runs `dotf agents -ic`
- **THEN** the system SHALL run the agents install bundle first
- **THEN** only if install succeeds, the system SHALL run the unified agents config sync

#### Scenario: Config then doctor
- **WHEN** the user runs `dotf agents -cd`
- **THEN** the system SHALL run the unified agents config sync first
- **THEN** only if config succeeds, the system SHALL run agents doctor

#### Scenario: Doctor alone
- **WHEN** the user runs `dotf agents -d`
- **THEN** the system SHALL run agents doctor without requiring a preceding sync in the same invocation

### Requirement: Agents 聚合安装边界
`dotf agents -i` SHALL 安装注册表中声明受支持的 agent CLI 工具包；`dotf <tool> -i` SHALL 只安装指定工具。聚合安装与单工具安装均 SHALL 通过 planner 展开依赖并产生独立动作结果。

#### Scenario: 安装 agents 工具包
- **WHEN** 用户运行 `dotf agents -i`
- **THEN** 计划 SHALL 展示将安装的各 agent CLI
- **THEN** 每个工具 SHALL 产生可识别的动作结果

#### Scenario: 单独安装 Claude
- **WHEN** 用户运行 `dotf claude -i`
- **THEN** SHALL 只安装 Claude CLI 及其显式依赖
- **THEN** SHALL NOT 安装其它 agent CLI

### Requirement: Agents 配置和诊断遵循统一生命周期
agents 的聚合 sync 与深度 doctor SHALL 通过标准 config/doctor 处理器接入 runner，保持现有 scope/profile 能力和脱敏要求，不得绕过统一计划、结果与失败传播。

#### Scenario: Agents 配置失败
- **WHEN** agents config 中任一必须同步步骤失败
- **THEN** runner SHALL 将该动作标记为 failed
- **THEN** 后续 doctor SHALL NOT 自动执行

#### Scenario: Agents JSON 诊断
- **WHEN** 用户运行 `dotf agents -d --deep --json`
- **THEN** 深度诊断 SHALL 输出机器可读且凭据脱敏的结果

### Requirement: Skill apply 与 remove 入口
系统 SHALL 提供不依赖 TUI 的 CLI，对单个 Skill 执行 apply 或 remove。入口 SHALL 写入本机 Desired Set 并在同一次调用中触发对应 sync / prune。未锁定 Skill SHALL 被拒绝。OpenSpec 生成的 skill 名称 SHALL 被拒绝。该入口 SHALL 支持 `--dry-run` 与 `--yes`。

#### Scenario: apply 一条 Locked Skill
- **WHEN** 用户对 lock 已批准的 Skill 运行 apply
- **THEN** 系统 SHALL 把该 Skill 加入本机 Desired Set
- **THEN** SHALL sync 其 runtime bundle
- **THEN** SHALL NOT 修改仓库编目

#### Scenario: remove 一条 Skill
- **WHEN** 用户对已在 Desired Set 中的 Skill 运行 remove 且确认
- **THEN** 系统 SHALL 把它移出 Desired Set
- **THEN** SHALL prune owned 且未漂的目标
- **THEN** 随后普通 `dotf agents -c` SHALL NOT 再安装它

#### Scenario: 拒绝 OpenSpec skill
- **WHEN** 用户对 `openspec-apply-change` 请求 apply 或 remove
- **THEN** 系统 SHALL 以非零退出并说明该 Skill 不在 Desired Set 管理范围

### Requirement: MCP Entry apply 与 remove 入口
系统 SHALL 提供不依赖 TUI 的 CLI，对一条 MCP Entry 执行 apply 或 remove。默认 MUST 指定目标工具；省略工具且未显式选择全部工具时 SHALL 失败。remove SHALL 只从该工具结构化配置中去掉这一条。全部工具模式 SHALL 显式请求。该入口 SHALL 支持 `--dry-run` 与 `--yes`，且 SHALL NOT 接受或打印密钥值。

#### Scenario: 按工具 remove
- **WHEN** 用户对 Cursor 上的 `web-reader` 运行 remove
- **THEN** 系统 SHALL 更新 overlay 中该工具的排除或停用
- **THEN** SHALL 从 Cursor 的 MCP 配置去掉该 Entry
- **THEN** 其它工具的同名 Entry SHALL 保持

#### Scenario: 未指定工具则失败
- **WHEN** 用户 remove 一条 MCP 且既未给工具也未选择全部工具
- **THEN** 系统 SHALL 以非零退出并提示需要 `--tool` 或全部工具旗标

#### Scenario: apply 不收集密钥
- **WHEN** 某 MCP Server 需要环境变量
- **THEN** apply 计划 SHALL 列出变量名
- **THEN** CLI SHALL NOT 提示用户输入密钥明文

