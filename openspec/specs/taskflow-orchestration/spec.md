# taskflow-orchestration Specification

## Purpose
定义 taskflow 的编排约定：用一个 driver change 承载任务身份与生命周期，把实现拆成若干子 change，全流程复用 stock openspec 命令，不引入第二份任务账本。
## Requirements
### Requirement: Driver change 是任务的唯一身份

`taskflow-new` SHALL 为每个任务创建且仅创建一个名为 `{task}-driver` 的 OpenSpec change 作为任务身份。该 change MUST 在 `.openspec.yaml` 中设置 `skip_specs: true` 且不携带 spec 增量。taskflow MUST NOT 创建 `tasks/` 台账目录、任务索引文件或任何编号体系。

#### Scenario: 创建 driver change

- **WHEN** 用户执行 `taskflow-new {任务描述}`
- **THEN** Agent 归纳 kebab-case 的 `{task}` 并运行 `openspec new change {task}-driver`
- **THEN** `.openspec.yaml` 含 `skip_specs: true`
- **THEN** 不产生 `openspec/changes/` 之外的任何任务状态文件

#### Scenario: driver 通过严格校验

- **WHEN** 对刚创建并写好 proposal 与 tasks 的 driver 运行 `openspec validate --strict --type change {task}-driver`
- **THEN** 校验通过
- **THEN** `openspec status --change {task}-driver --json` 中 specs 的 status 为 `skipped`

#### Scenario: 任务清单来自 openspec

- **WHEN** 需要列出进行中的任务
- **THEN** 以 `openspec list` 的结果为准
- **THEN** 不存在由 taskflow 维护的第二份任务索引

### Requirement: driver 正文自带协议

`taskflow-new` SHALL 把 driver 协议、涉及面表与验收标准写入 driver 的 `proposal.md`。协议 MUST NOT 依赖 `openspec/config.yaml` 的 `operations.*.guidance` 或对 stock `openspec-*` skill 的修改。

#### Scenario: 协议随 change 进入上下文

- **WHEN** stock `openspec-apply-change` 对 driver 运行并读取 `openspec instructions apply --json` 给出的 `contextFiles`
- **THEN** driver 的 `proposal.md` 在其中
- **THEN** 协议文本无需额外配置即被读取

#### Scenario: 协议随 change 跨仓可移植

- **WHEN** driver change 被放到另一个未做任何 taskflow 配置的 openspec root
- **THEN** 协议仍完整存在于该 change 内部
- **THEN** 工作流无需在该仓预置 `config.yaml` 规则即可执行

### Requirement: driver 的 tasks.md 由 propose 生成并登记子 change

`taskflow-new` MUST NOT 写 driver 的 `tasks.md`。该文件 SHALL 由 stock `openspec-propose` 在读取 driver `proposal.md` 后生成，并为每个拆出的子 change 登记独立条目。子 change SHALL 命名为 `{task}-<slice>`。

#### Scenario: 脚手架留出 tasks 空缺

- **WHEN** `taskflow-new` 执行完毕
- **THEN** `openspec status --change {task}-driver --json` 显示 proposal 为 `done`、tasks 尚未完成
- **THEN** 后续 `openspec-propose` 有待生成的 artifact，不会空转

#### Scenario: 子 change 在 propose 阶段备齐

- **WHEN** 对 driver 执行 `openspec-propose`
- **THEN** 每个子 change 的 artifacts 在该阶段创建完成
- **THEN** driver 的 `tasks.md` 为每个子 change 至少登记一条实施条目

#### Scenario: 命名前缀可枚举全家

- **WHEN** 在 driver 所在 planning root 运行 `openspec list`
- **THEN** driver 与其子 change 共享 `{task}` 前缀
- **THEN** 无需额外元数据即可辨认归属

### Requirement: 进度只认 OpenSpec checkbox

实现进度 SHALL 完全由 checkbox 表达：子 change 的 `tasks.md` 记实现进度，driver 的 `tasks.md` 记编排进度。driver 的某条实施 checkbox MUST 在对应子 change 全部 checkbox 已勾且 `openspec validate --strict` 通过之后才允许勾选。taskflow MUST NOT 持久化第二份完成度、暂缓或分支状态记录。

#### Scenario: 编排进度滞后于实现进度

- **WHEN** 子 change `{task}-api` 仍有未勾 checkbox
- **THEN** driver 中对应的实施条目保持未勾

#### Scenario: 未完成项不伪装成已完成

- **WHEN** 某条 driver checkbox 因依赖、环境或授权无法推进
- **THEN** 该 checkbox 保持未勾，原因写入 driver `proposal.md` 的验证记录小节
- **THEN** Agent 继续处理不依赖它的其余条目

#### Scenario: 结束一轮时逐条交代

- **WHEN** 一轮 apply 结束且仍有未勾 checkbox
- **THEN** 报告逐条列出未勾条目与原因
- **THEN** 不以按 change 汇总的数量代替逐条说明

### Requirement: 子 change 先归档，driver 最后归档

driver 的 `tasks.md` SHALL 在收尾段为每个子 change 登记一条归档 checkbox，使子 change 在 apply 阶段完成归档。`openspec-archive {task}-driver` SHALL 只归档 driver 自身。

#### Scenario: 归档顺序

- **WHEN** driver 全部 checkbox 已勾
- **THEN** 所有子 change 已通过 `openspec archive` 移入 `openspec/changes/archive/`
- **THEN** 此时对 driver 执行 stock 归档不需要任何递归处理

#### Scenario: 归档不依赖注入钩子

- **WHEN** 检视归档路径所需的前置条件
- **THEN** 不依赖 `openspec instructions archive` 的 `operationGuidance`
- **THEN** 不要求修改 stock `openspec-archive-change` skill

### Requirement: 涉及面与交付分支由 driver 正文驱动

driver 的 `proposal.md` SHALL 含涉及面表，角色取值为 `必须`、`建议`、`排除`。分支准备 SHALL 表现为 driver `tasks.md` 中的 checkbox，且只处理角色为 `必须` 的仓。遇到非目标分支的未提交改动或 fetch 失败时 Agent MUST 停下并交由用户处理，MUST NOT 自动执行 stash、reset 或强制切换。

#### Scenario: 只准备必须仓

- **WHEN** 执行分支准备 checkbox
- **THEN** 只有角色为 `必须` 的仓被切到任务分支
- **THEN** `建议` 与 `排除` 仓保持只读

#### Scenario: 脏工作区停下等人

- **WHEN** 某个必须仓存在未提交改动或 origin fetch 失败
- **THEN** Agent 报告该仓并等待用户处理
- **THEN** 已准备成功的仓保留现状以便重试

### Requirement: 命令面只增一个且零脚本

taskflow SHALL 只新增 `taskflow-new` 一个 command，其余阶段复用 stock `openspec-*` skill。skill 目录 MUST NOT 包含 `scripts/`，且 MUST NOT 要求 `scripts/agents/sync.py` 新增 shim。

#### Scenario: 阶段命令复用 stock

- **WHEN** 用户走完 explore、propose、apply、archive 四个阶段
- **THEN** 每一步调用的都是 stock `openspec-*` skill，参数为 `{task}-driver`
- **THEN** taskflow 未为这些阶段定义新 command

#### Scenario: 零脚本

- **WHEN** 检视 `agents/skills/taskflow/`
- **THEN** 其中没有可执行脚本目录
- **THEN** `scripts/agents/sync.py` 的 `SHIMS` 未新增条目

