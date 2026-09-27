# Loop Protocol

## Stage 0 — Dependency and mode check

记录四项后再动：

```text
goal: <逐字原文>
mode: normal | benchmark
budget: <用户给定预算，或 loop-control: slices=1-3; repairs-per-slice<=2; full-chain=1>
evidence_root: <项目约定临时目录，或 /tmp/delivery-loop/<slug>>
```

检查依赖 skill 可读。缺依赖时停止；不手写替代 OpenSpec / taskflow / reviewer 流程。

`<slug>` 由目标归纳为 kebab-case；同名冲突时追加运行时间戳或唯一 run id。`evidence_root` 一旦写入 manifest，本轮不得改路径；后续报告只引用该路径。

## Stage 1 — Intent and complexity

- 复杂信号：项目级重构、多个主页面、两个以上角色 / 权限、跨请求或用户复用持久化数据、外部集成、实时协作、通知 / 审计、业务面广。
- 简单局部修改：退出 delivery-loop，说明直接执行即可。
- 目标过短但复杂：按最合理解释生成质量画像；除危险、线上、降级确认外不追问。normal 的画像经 task-wizard / task-explore 门禁冻结；benchmark 在派发实现前由编排者冻结一份评审专用画像并记录哈希，不发给实现者。

调用 task-wizard 生成 Goal 方案。用户点名 delivery-loop 视为接受自动编排和推荐路由，不视为授权危险操作。

## Stage 2 — Explore and freeze

复杂目标必须走 task-explore：

1. `new` 登记上游方案、完成判据、质量画像与降级原文快照。
2. `explore` 补齐未知，不重复已查事实。
3. `design` 展开页面、状态、数据、验收与风险。
4. `decide` 冻结方案；pending 降级未确认不得冻结。

## Stage 3 — Taskflow handoff

交给 taskflow 建 `{task}-driver`。driver proposal 必须保留：

- 完成判据原文
- 质量画像原文快照
- 显式降级表
- 窄切片拆分
- 证据要求

从现在起，不另建进度账本；delivery-loop 只根据 driver / 子 change checkbox 汇报状态。

## Stage 4 — Narrow slice

首轮只选 1-3 个核心闭环。每个闭环写清：

- 入口
- 用户动作
- 结束状态
- 失败路径
- 自动化测试
- 运行时证据

不先铺全量功能。窄切片失败时先归因，不继续堆实现。

## Stage 5 — Implementation dispatch

### normal

实现者必须收到：

- 目标原文
- 质量画像原文，或保留语义的子范围裁剪
- 本切片验收要求
- 工作区、依赖、时间与安全约束

不要求实现者看完整评分 rubric 或无关子 change。

### benchmark

按 [benchmark-isolation.md](benchmark-isolation.md)：只给目标原文和运行约束，不给画像、rubric、期望页面清单或审阅意见。

## Stage 6 — Evidence

先证据，后评分。至少收集：

- 启动命令与输出
- 自动化测试结果
- 关键流程截图或导出日志
- 失败与修复对照
- 代码 / 依赖状态

具体清单见 [evidence-report.md](evidence-report.md)。

## Stage 7 — Role review

调用：

```text
role-based-reviewer mode=review roles=product,design,engineer
```

评分维度、UI/UX 六子项与通过线的真相源是 [../../taskflow/references/acceptance-rubric.md](../../taskflow/references/acceptance-rubric.md)。delivery-loop 不复制第二份 rubric 或数字口径；报告引用当次代码 / skill 状态。
要求返回：

- product / design / engineer 独立 findings
- Blocker / Major / Minor
- 五维评分
- UI/UX 六子项评分
- 证据缺口

实现者自评只作输入，不算通过线。

## Stage 8 — Failure triage

每条 Blocker / Major 必须归因：

| 类型 | 判据 | 处置 |
|---|---|---|
| skill gap | 规则缺失、矛盾或无法指导正确执行；换任务仍会错 | 调 skill-upgrader，先 patch 后应用 |
| implementation bug | 规则正确，实现错误 | 修交付仓并补回归测试 |
| acceptance gap | 验收标准或评分维度漏项 | 补验收标准 / rubric，再复验 |

一类失败可有多条归因，但必须逐条写清，不合并。

驳回门：把 finding 驳回为「设计内 / not a bug」MUST 附决策推导——设计文档、token 注释、
比例依据等可追溯记录；拿不出推导时 MUST 按 acceptance gap 处理（补验收标准再复验），
MUST NOT 维持驳回。验证全绿 MUST NOT 构成设计正确性证据：一致性契约只能证明
「实现符合约定」，评审驳回任何 finding 前必须先问「这个约定本身怎么来的」。

归因自检：

1. 同一 finding 在闭环内若被给出第二种解释（含驳回改修复、修复改驳回、表层修复改深层
   修复），MUST 先停下重做归因，MUST NOT 沿新解释直接改交付仓；重做后须写明前一解释
   为何不成立。解释翻新本身就是归因未收敛的证据，不是「想得更清楚了」。
2. acceptance gap 类修复 MUST 区分层次：补验证（让断言锚定既有取值）与补设计决策依据
   （追问取值本身怎么来的）是两条不同路径。只在验证层修时 MUST 明确记录「设计决策依据
   未补」，MUST NOT 默认已收敛——表层修复会让验证更全，同时把错误的约定固化得更牢。
3. 修复收敛后 MUST 追问一次泛化性：这个失败换个项目 / 换个模块还会不会发生？会 →
   同时走 skill gap 路径沉淀通用规则；不会 → 允许留在交付仓。不追问不得标记该 finding 收敛。

## Stage 9 — Repair loop

每个窄切片最多两轮修复：

1. 第一轮修复后重跑受影响静态门 / 窄切片。
2. 仍有 P0/P1 时第二轮修复并重跑。
3. 第二轮后仍有 P0/P1：停止，不继续扩展全量。

skill gap 的 patch 必须通过 `git apply --check` 后应用，并重跑受影响检查。

## Stage 10 — Full-chain validation

所有窄切片通过后，最后跑一次全链路：

- 跨切片导航 / 数据一致性
- 核心工作流
- 错误与空态
- 全量自动化测试
- 明暗 / 窄屏等 UI 证据（如任务有 UI）
- 运行时日志或截图
- pending 降级为 0

不为“安心”重复跑与改动无关的全量验证。

## Stop conditions

立即停止并报告：

- 缺依赖 skill
- 需要用户确认 pending 降级
- 危险操作、线上动作、泄密风险
- reviewer 派不出或无结论
- 同一验证连续失败两次
- 同一窄切片两轮修复后仍有 P0/P1
- 预算耗尽
- driver checkbox 全勾但完成判据不成立

停止报告必须写明已完成、未完成、证据、下一步，不把部分结果说成完成。

## 增量验证协议

每个切片与每轮修复都按这四条执行；Stage 10 的全链路不受影响，仍跑一次。

1. **变更→门禁映射**：切片开工前声明触碰面（模块 / 路由 / 组件 / UI surface 与状态），
   列出受影响门禁（静态门、目标单测、运行态契约、截图键）；只跑映射内的门禁。
   映射声明写进 evidence manifest，作为「为什么没跑某项」的审计依据。
2. **证据复用**：截图与日志按 `(surface, state, viewport, theme)` 键写入 manifest；
   复跑时未受影响的键直接引用既有产物，不重新生成；受影响的键必须重新生成，
   不许用旧图充新证据。
3. **fail-fast 顺序**：静态门 → 目标单测 → 运行态契约 → 截图矩阵；前一层红了
   不跑后一层，修完从红的那层继续。
4. **可中断步骤 checkpoint**：耗时步骤（全量套件、截图矩阵、全量 contrast）
   每完成一个键/用例先把结果落盘再汇总；任何时刻被中断，已完成的键可直接用于
   回填任务状态与 manifest，不整轮作废。编排者被中断后恢复时先读 manifest，
   只补缺失键。
