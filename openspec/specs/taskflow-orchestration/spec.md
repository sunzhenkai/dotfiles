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

taskflow SHALL 只新增 `taskflow-new` 一个 command，其余阶段复用 stock `openspec-*` skill。skill 目录 MUST NOT 包含 `scripts/`，且 MUST NOT 要求 `src/agents/sync.py` 新增 shim。

#### Scenario: 阶段命令复用 stock

- **WHEN** 用户走完 explore、propose、apply、archive 四个阶段
- **THEN** 每一步调用的都是 stock `openspec-*` skill，参数为 `{task}-driver`
- **THEN** taskflow 未为这些阶段定义新 command

#### Scenario: 零脚本

- **WHEN** 检视 `agents/skills/taskflow/`
- **THEN** 其中没有可执行脚本目录
- **THEN** `src/agents/sync.py` 的 `SHIMS` 未新增条目

### Requirement: 完成判据写入验收标准第一条

`taskflow-new` 收到的任务描述含完成判据时，driver `proposal.md` 的验收标准第一条 MUST 是该判据，且为 checkbox。任务描述没有完成判据时，验收标准按原方式填写，MUST NOT 编造判据。Driver 协议小节的固定文本 MUST 保持逐字不变。进度仍只认 checkbox：该条验收标准不得单独代替 driver `tasks.md` 的编排完成。

#### Scenario: 交接带入判据

- **WHEN** `taskflow-new` 的任务描述含一条完成判据
- **THEN** driver `proposal.md` 验收标准的第一条 checkbox 为该判据原文
- **THEN** Driver 协议小节与固定模板逐字一致

#### Scenario: 没有判据时不新增第一条

- **WHEN** `taskflow-new` 的任务描述没有完成判据
- **THEN** 验收标准中不出现编造的完成判据条目

#### Scenario: 验收标准不代替编排进度

- **WHEN** 验收标准第一条已写下，但 driver `tasks.md` 仍有未勾项
- **THEN** 编排进度仍以未勾的 `tasks.md` 为准


### Requirement: 质量画像与降级进入 proposal 与验收

任务描述含质量画像或显式降级原文时，driver `proposal.md` 的 `Why` MUST 逐字保留原文快照，不摘要、不改写、不用路径替代。验收标准 MUST 在完成判据之外检查：画像快照已进入 proposal；每条角色底线有运行时行为、截图或测试证据；`pending` 降级数为 0；`confirmed` 降级在验证记录中逐项可追踪。任务描述没有画像时 MUST NOT 编造。子 change 实施中发现新的生产性降级时 MUST 标 `pending`，写入验证记录，并作为「需要用户决策」停下；用户点名接受或明确全部确认后才改为 `confirmed`，才允许勾相关验收。执行者、子代理、审阅收敛都 MUST NOT 代用户确认。Driver 协议固定文本 MUST 保持逐字不变。

#### Scenario: 上游画像进入 proposal 与验收

- **WHEN** taskflow 收到含质量画像与显式降级原文的任务描述
- **THEN** `Why` 保留原文快照
- **THEN** 验收标准包含画像快照、角色底线证据、pending=0 与 confirmed 追踪

#### Scenario: 新降级需要用户决策

- **WHEN** 子 change 实施中发现比默认期望少交付的新约束
- **THEN** 该项标 `pending` 并写入验证记录
- **THEN** 相关验收保持未勾，直到用户确认后改 `confirmed`

#### Scenario: 无画像不编造

- **WHEN** 任务描述没有质量画像
- **THEN** proposal 与验收标准不新增画像条目
- **THEN** 完成判据与编排进度规则保持不变

### Requirement: 交付质量闭环与验收 rubric

复杂交付的收尾段 MUST 按三层验证执行：静态门、窄切片、全链路；窄切片 MUST 先行，全链路 MUST 只在收尾跑一次。窄切片或全链路失败时，系统 MUST 先归因为 skill gap、implementation bug 或 acceptance gap 之一，再分别处置：skill gap 走对应 skill 的 `patches/` 出可审计 patch，implementation bug 在交付仓修复并补回归测试，acceptance gap 补 rubric 或验收标准。修复后 MUST 先重跑受影响切片，再跑全链路，MUST NOT 与改动无关地全量重跑。

最终验收 MUST 按五维评分：功能闭环、UI/UX、工程质量、画像一致性、证据；UI/UX MUST 拆为信息架构、视觉层级、关键状态、反馈、无障碍、响应式六个子项。通过线为五维均 ≥2 且 UI/UX 六子项均值 ≥2.5，任一 UI/UX 子项为 0 时 MUST NOT 通过。评分 MUST 先收证据再打分，评分主体按岗位分工；实现者自评 MUST NOT 代替岗位评分。缺分或缺证据时 MUST NOT 勾验收标准 checkbox。

派发实现者时 MUST 隔离验收期望：实现者只接收样例或需求原文与运行约束，MUST NOT 接收质量画像、验收 rubric、期望页面清单或审阅意见。审阅者持有画像与 rubric；复跑 MUST 使用同一份原文，MUST NOT 追加事后提示。评分与证据 MUST NOT 构成 checkbox 之外的第二份完成度；进度仍只认 checkbox。

#### Scenario: 窄切片先行且失败先归因

- **WHEN** 复杂交付首次实现或大改之后需要回归
- **THEN** 先跑静态门与窄切片，不先铺全量功能
- **THEN** 失败先归因为 skill gap、implementation bug 或 acceptance gap，再分别处置

#### Scenario: 修复后只重跑受影响切片

- **WHEN** skill gap 或 implementation bug 已修复
- **THEN** 先重跑受影响的那一层
- **THEN** 通过后再跑一次全链路，不做无关全量重跑

#### Scenario: 五维与 UI 六子项通过线

- **WHEN** driver 收尾准备回填验收标准
- **THEN** 按功能闭环、UI/UX、工程质量、画像一致性、证据五维出分
- **THEN** 五维均 ≥2 且 UI/UX 六子项均值 ≥2.5 才通过，任一子项为 0 不通过

#### Scenario: 缺分或缺证据不勾验收

- **WHEN** 五维存在缺分，或证据不齐
- **THEN** 不勾验收标准 checkbox
- **THEN** 不用实现者自评代替对应岗位评分

#### Scenario: 实现者输入隔离

- **WHEN** 派发复杂交付的实现者
- **THEN** 实现者只收到样例或需求原文与运行约束
- **THEN** 质量画像、验收 rubric、期望页面清单与审阅意见只由审阅者持有

#### Scenario: rubric 不成为第二份账本

- **WHEN** 已给出五维分数与证据
- **THEN** 进度仍只认 checkbox，分数与证据不构成第二份完成度
