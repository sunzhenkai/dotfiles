# task-wizard-goal Specification

## Purpose

定义处在 goal 里时 Goal 方案的可重入状态与路由下一跳，审阅者与方案置信度对开工的门禁，以及完成判据和下游账本汇合后才标完成的条件。

## Requirements

### Requirement: Goal 方案与任务方案分流

处在 goal 里（消息中有 `/goal`，或已有进行中的 goal 且本条消息挂了 task-wizard）时，系统 MUST 只产出 Goal 方案。没有进行中的 goal 时，系统 MUST 只走任务方案，并在写出后停下等人选择。任务方案的确认、三档路由与边界 MUST 保持原有行为。

#### Scenario: 处在 goal 里不写任务方案

- **WHEN** 消息中有 `/goal`，或已有进行中的 goal 且本条消息挂了 task-wizard
- **THEN** 回复前部是 Goal 方案
- **THEN** 不出现任务方案的「按此执行 / 调整哪步 / 改路由」对齐问句

#### Scenario: 没有 goal 时不进入 Goal 方案

- **WHEN** 没有进行中的 goal，且消息中没有 `/goal`
- **THEN** 只产出任务方案并停下等人选择

### Requirement: 方案正文携带状态与下一跳

Goal 方案 MUST 写在当轮回复前部，MUST NOT 落成文件。正文 MUST 含完成判据、步骤、退出点、方案置信度、状态、路由。状态只允许 `执行中`、`已停`、`已交接`、`已完成`。方案置信度只允许 `高`、`中`、`低`。路由 MUST 只描述该状态的下一跳。退出、升档、交接、做完时，系统 MUST 改写状态与路由，使最后一份方案等于当前状态。

#### Scenario: 半屏不够时仍留下状态机

- **WHEN** Goal 方案超过半屏
- **THEN** 可以压缩前提与坑
- **THEN** 完成判据、步骤、退出点、方案置信度、状态、路由仍在

#### Scenario: 旧方案没有状态行

- **WHEN** 后续回合读到一份没有「状态」的 Goal 方案
- **THEN** 路由为 `本会话直接做` 时按 `执行中` 续做，并在当轮回复补上状态
- **THEN** 路由以 `先停` 开头时按 `已停` 处理，并在当轮回复补上状态

### Requirement: 四个状态的下一跳

`执行中` MUST 从第一个未验证步骤继续，直到完成判据成立或改为 `已停`。判据成立时 MUST 改为 `已完成`，停止新增工作，并对照判据说明；环境能把 goal 标成完成时 MUST 标完成。`已停` MUST 只执行用户已经点名授权的那一件事。单独「继续」MUST NOT 构成授权，状态保持 `已停`，且不新增工作。`已交接` MUST NOT 重出 Goal 方案；按路由中的账本继续。该账本的完成条件成立且完成判据成立时，才改为 `已完成`。改步骤 MUST 仅在状态为 `执行中`、完成判据不变、档位仍为简单时发生。

#### Scenario: 简单档跨回合续做

- **WHEN** 状态为 `执行中`，本轮未做完，下一轮 skill 不再挂上
- **THEN** 从第一个未验证步骤继续
- **THEN** 不把方案重写成任务方案

#### Scenario: 单独继续仍停

- **WHEN** 状态为 `已停`，用户只回复「继续」
- **THEN** 状态仍为 `已停`
- **THEN** 不新增工作，不把 goal 标成完成

#### Scenario: 完成判据成立

- **WHEN** 状态为 `执行中` 且完成判据成立
- **THEN** 状态改为 `已完成`，停止新增工作，回复对照判据说明已完成
- **THEN** 环境能标完成时把 goal 标成完成

### Requirement: 不套模板仍留下已停

原因还不清要先排查，或要定接口、架构的详细设计时，系统 MUST NOT 套用完整步骤正文，MUST NOT 新增工作。回复 MUST 仍写出状态 `已停` 与路由：排查指向等用户明确说走 task-explore；详细设计标明本流程不做。

#### Scenario: 排查停在 task-explore 入口

- **WHEN** Goal 任务要先排查、写不出可执行步骤
- **THEN** 不写步骤正文，不新增工作
- **THEN** 状态为 `已停`，路由等用户明确说走 task-explore

#### Scenario: 详细设计直接停

- **WHEN** Goal 任务要定接口或架构
- **THEN** 状态为 `已停`，路由标明本流程不做详细设计
- **THEN** 不新增工作

### Requirement: 退出点改写为已停

方案 MUST 列出这些退出点标签：理解不够、方案置信度不足、阻塞解不开、未点名的危险操作、线上动作、同一验证连败两次、泄密、执行中升档、审阅不通过、审阅派不出、审阅没有结论。正文 MUST 写明：命中后把状态改为 `已停`，路由写成所需要的授权；单独「继续」不算授权。危险操作在任务描述点名后可以做；线上动作与泄密即使任务描述点名也 MUST 停。`已交接` 期间命中退出点 MUST 把状态改回 `已停`。退出点 MUST NOT 把 goal 标成完成。多条同时命中时 MUST 一次说清。

#### Scenario: 退出后路由不再是开工句

- **WHEN** 执行中撞上退出点
- **THEN** 状态改为 `已停`，路由点名需要的授权
- **THEN** 不把 goal 标成完成

#### Scenario: 交接期间泄密仍停

- **WHEN** 状态为 `已交接`，且下一步要把密钥、令牌、内部 URL 或公司代码写入公开仓库
- **THEN** 状态改回 `已停`
- **THEN** 不新增写入，不标完成

### Requirement: 升档改路由而不终局

开工后发现已是中等或复杂时，系统 MUST 立刻停止改代码，把状态改为 `已停`，并把路由换成对应档位的交接句。已经改过的可逆部分留在工作区，MUST NOT 自动回滚。

#### Scenario: 简单档执行中升为复杂

- **WHEN** 状态为 `执行中`，执行中发现任务要拆多段或跨仓
- **THEN** 停止改代码，状态改为 `已停`
- **THEN** 路由改为复杂档交接句，不再保留「本会话直接做」

### Requirement: 中等路由实施到 checkbox

方案置信度为高且档位为中等时，系统 MUST 把状态改为 `已交接`，MUST 直接 `openspec-propose` 再 `openspec-apply-change`，方案正文原样带入。该路径 MUST NOT 等待用户说走 OpenSpec，也 MUST NOT 走 grill-with-docs。进度 MUST 只认该 change 的 `tasks.md` checkbox。全勾且完成判据成立才改为 `已完成`。未完则下一轮从第一个未勾项继续，MUST NOT 重出 Goal 方案。下游 skill 读不到时 MUST 停并给出安装选项，MUST NOT 发明等价命令。

#### Scenario: 中等且高置信度直接进入 OpenSpec

- **WHEN** 方案置信度为高，且档位为中等
- **THEN** 状态为 `已交接`
- **THEN** 当轮开始 `openspec-propose`，不走 grill-with-docs

#### Scenario: 提案写完仍不算做完

- **WHEN** `openspec-propose` 已完成但 `tasks.md` 仍有未勾项
- **THEN** 状态为 `已交接`
- **THEN** 不把 goal 标成完成，下一轮从第一个未勾项继续 apply

### Requirement: 复杂路由遵守探索门禁

方案置信度为高且档位为复杂时，建议 MUST 已经写入步骤。同一轮 MUST 只出方案、不改代码，状态为 `已停`，直到用户明确说走 task-explore。其后状态为 `已交接`。路由 MUST 写明：没有 `tasks/` 时先等用户确认再创建；slug 由 task-explore 推断，wizard MUST NOT 另起任务名；`new` 时把完成判据、步骤、阻塞点、坑登记进 `TASK.md` 的「方案」；`new` 之后由用户选择 explore 或 chat；`decide` 用完成判据作为成功标准；用户确认冻结后才 `handoff`。交接前的创建目录、冻结、脏工作区选择是下游门禁，MUST NOT 标 goal 完成，也 MUST NOT 重出 Goal 方案。`handoff` 之后进度只认 driver 的 checkbox。driver checkbox 全勾且完成判据成立才改为 `已完成`。中等路径在交接后发现要拆多段时，MUST 把状态改回 `已停` 并换成复杂路由，等用户再说走 task-explore。

#### Scenario: 未授权不创建探索任务

- **WHEN** 方案置信度为高，档位为复杂，且用户尚未说走 task-explore
- **THEN** 状态为 `已停`
- **THEN** 不创建 `tasks/`，不改代码

#### Scenario: 交接不等于完成

- **WHEN** task-explore 已进入 `handed-off`，driver 的 `tasks.md` 仍有未勾项
- **THEN** Goal 状态为 `已交接`
- **THEN** 不把 goal 标成完成

#### Scenario: driver 做完且判据成立

- **WHEN** driver checkbox 全勾，且 Goal 方案里的完成判据成立
- **THEN** 状态改为 `已完成`，对照判据说明，能标完成则标完成

#### Scenario: checkbox 全勾但判据不成立

- **WHEN** driver checkbox 全勾，但完成判据不成立
- **THEN** 状态改为 `已停`，不标完成

### Requirement: 审阅者先于开工

写完 Goal 方案、改代码之前，系统 MUST 叫一次审阅者。状态为 `执行中` 且出现新的决策点时 MUST 再叫。执行者写不出方案时 MUST 直接退出点「理解不够」，MUST NOT 叫审阅者。方案里已有线上动作、泄密或未点名的危险操作时 MUST 直接 `已停`，MUST NOT 叫审阅者。审阅者 MUST 只读，一次返回方案置信度、每个决策点一条建议、以及缺陷。

默认审阅者 MUST 是当前宿主拉起的子 agent，优先更强模型；当前已是最强档时 MUST 另起一个同模型子 agent，并在方案里记「无更强档」。起不来 MUST 换下一个可用模型，最多两次；两次都没有审阅结论时 MUST `已停`，退出点「审阅没有结论」。执行者自己给出的档位 MUST NOT 算审阅结论。

goal 原文或当轮用户消息写了 `agent-roster` 时，系统 MUST 委托 `$agent-roster` 做名册审阅。点名了唯一 Endpoint 时 MUST 走其快速路径。只说用名册、没点名谁时，MUST 按 routing 选一个最匹配的直接派，MUST NOT 列出候选表等人圈选。执行器不可用、证据不足或还要人时，MUST `已停`，退出点「审阅派不出」，MUST NOT 改回本机子 agent。

方案置信度为高时，系统 MUST 把建议写入步骤，再次核对退出点后再进入档位路由。有缺陷时 MUST 改一轮再审一次；再审仍是高且缺陷仍在时 MUST `已停`，退出点「审阅不通过」。再审变为中或低时 MUST 按该档退出。完成判据要改或要升档时 MUST 走对应退出点。

方案置信度为中时，系统 MUST `已停`，退出点「方案置信度不足」，MUST 保持当前步骤，回复 MUST 写明档位、差在哪、未采纳的建议。方案置信度为低时，系统 MUST `已停`，退出点「理解不够」，MUST 保持当前步骤，并给出建议的完成判据。

「仍按此方案执行」MUST 只放行当前步骤这份方案，MUST NOT 把未采纳的建议写入步骤，也 MUST NOT 立刻再审。单独「继续」MUST NOT 构成这句授权。要按建议走，用户 MUST 另说一件已经点名的事。步骤或完成判据因此再变时 MUST 重新审。放行之后，简单档 MUST 改为 `执行中` 并继续；中等档 MUST 改为 `已交接` 并按中等路由开工；复杂档 MUST 保持 `已停`，直到用户说走 task-explore。

#### Scenario: 高置信度写入建议

- **WHEN** 审阅者给出方案置信度高，并给出一条建议
- **THEN** 建议写入步骤
- **THEN** 再次核对退出点之后才按档位继续

#### Scenario: 中置信度保持原步骤

- **WHEN** 审阅者给出方案置信度中
- **THEN** 状态为 `已停`，退出点为「方案置信度不足」
- **THEN** 步骤保持审阅前的正文
- **THEN** 回复写明未采纳的建议

#### Scenario: 放行句不采纳建议

- **WHEN** 因方案置信度不足而 `已停`，用户说「仍按此方案执行」
- **THEN** 按当前步骤继续
- **THEN** 未采纳的建议不写入步骤

#### Scenario: 名册派不出

- **WHEN** goal 原文写了 `agent-roster`，且名册执行器不可用
- **THEN** 状态为 `已停`，退出点为「审阅派不出」
- **THEN** 不改用本机子 agent
