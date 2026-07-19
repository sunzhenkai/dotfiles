## Requirements

### Requirement: 分系统 init 入口
系统 SHALL 提供 `dotf init` 作为面向操作系统的初始化入口。未指定 OS 时 SHALL 自动检测当前系统并选择对应 profile；SHALL 支持 `--os <id>` 强制指定，以及 `--list` 列出可用 profile。

#### Scenario: 自动检测
- **WHEN** 用户运行 `dotf init` 且未传 `--os`
- **THEN** 系统检测当前 OS 并使用匹配的 profile

#### Scenario: 强制 OS
- **WHEN** 用户运行 `dotf init --os darwin`
- **THEN** 系统使用 darwin profile，即使当前机器不是 darwin

#### Scenario: 列出 profile
- **WHEN** 用户运行 `dotf init --list`
- **THEN** 输出可用 profile 标识（至少覆盖现有 system 分发所支持的主要 ID 族）

### Requirement: profile 默认全量力度
每个 OS profile 的默认行为 SHALL 依次包含：
1. 该系统的系统包/基础环境步骤（与现有 `system` 分发语义等价）；
2. 注册表中具备 install 且适用于该 OS 的全部模块；
3. 注册表中具备 config 且适用于该 OS 的全部模块。

即：**该 OS 上所有可装/可配都跑一遍**（不适用模块跳过）。各项仍须按既有确认策略交互（默认 N），不得静默跳过确认机制本身。

#### Scenario: Linux 跳过仅 macOS 模块
- **WHEN** 在 Linux 上执行 `dotf init`
- **THEN** 仅 darwin 适用的模块 SHALL NOT 被纳入本次 install/config 全集

#### Scenario: 包含系统步骤与双全集
- **WHEN** 用户确认执行某 OS 的 init
- **THEN** 流程 SHALL 包含系统包步骤、该 OS 全部可安装模块、该 OS 全部可配置模块

### Requirement: 全局全量与 init 区分
`dotf -i -a` / `dotf -c -a` / `dotf -a` SHALL 继续作为全局全量入口保留。全量安装/配置在枚举模块时 SHALL 按当前 OS 过滤不适用项，与 init 的 OS 适用性规则一致。`dotf -a` SHALL NOT 自动执行系统包分发步骤（该步骤专属 `init` / `system` 模块）。

#### Scenario: -a 不含 system 包分发
- **WHEN** 用户运行 `dotf -a`
- **THEN** 执行当前 OS 适用的全部 install 与全部 config
- **THEN** SHALL NOT 隐含执行完整 `dispatch_init` 系统包流程（除非 `system` 本身作为 install 模块被包含且用户确认）
