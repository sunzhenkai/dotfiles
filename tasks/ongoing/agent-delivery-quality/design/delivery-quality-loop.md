# 复杂 Goal 交付质量闭环

> 用同一个样例输入反复验证：先把质量要求写进方案，再让实现受画像和角色审阅约束，最后用小切片回归发现 skill 缺口并出可审计 patch。

> **真相源**：本文是案例设计与审计记录；通用执行规则已上移到 `agents/skills/taskflow/references/delivery-quality-loop.md`、`acceptance-rubric.md` 与 `implementer-isolation.md`。冲突时以共享 skill 为准。

## Context

- **Problem**: 功能齐全不等于可交付。复杂 Goal 缺少质量约束、角色审阅和显式降级确认时，agent 会把「看板页存在」当「可用看板」。
- **Stakeholders**: 请求交付的用户（验收价值）、实现 agent（需要可执行边界）、审阅 agent（需要可检查质量底线）、skill 维护者（需要通用规则和回归证据）。
- **Success criteria**:
  1. 复杂 Goal 方案缺质量画像时无法进入实现；补齐后画像字段和底线可逐条检查。
  2. 复杂档审阅强制包含 product / design / engineer 三个视角；实现与方案偏差能被归为 P0/P1。
  3. 每个生产性降级都有确认状态；未确认降级阻止完成。
  4. 画像、UI 规格、验收证据和降级表一路传入 task-explore 与 taskflow，driver 验收能引用原文。
  5. 窄切片失败必须归因为 skill gap / implementation bug / acceptance gap；skill gap 出可审计 patch，修复后受影响切片重跑通过，再扩展到全量。
- **Constraints**: 改动必须进入 `agents/skills/` 的 patch 协议；规则要开源可复用；不改 task-explore 生命周期状态机与 taskflow 编排协议；不引入全量生产基础设施门槛；本机验证产物写 `/tmp`。
- **Out of scope**: 不把某次 task-manager 的页面、数据库名或私有路径写进共享 skill；不让简单/中等任务强制做完整质量画像；不在本设计里写业务代码。

## Complex-tier trigger

复杂档沿用 task-wizard 现有定义，并补充产品交付硬指标：命中任一条即复杂，不得降档绕过质量门。

- 产品面跨多个主页面，或有两个以上生效角色/权限边界。
- 需要持久化数据，且数据会在多个请求或用户之间复用。
- 需要外部系统集成、实时协作、文件/通知/审计等跨模块行为。
- 需要项目级重构、逻辑重塑，或业务逻辑复杂且涉及面广。

仅改一个组件、单页原型、无持久化的静态演示不触发本节；仍按原档位路由。

## Current State

- task-wizard 已有 Goal 状态机、外部参照、审阅循环和 `role-based-reviewer` 显式接入；但复杂档仍不强制质量画像与固定三角色。
- task-explore 已把完成判据和方案带入 explore / decide / handoff；但质量画像与降级确认还不是登记和交接的一等内容。
- taskflow proposal 已要求完成判据进入验收标准；但没有质量画像引用和降级确认的固定位置。
- role-based-reviewer 默认克制，只有显式触发才加角色；复杂 Goal 工作流需要成为正当调用方。
- 上一版失败现场是 `/home/wii/tmp/task-manager`，只作回归事实，不在共享 skill 中引用绝对本机路径。

## 外部参照

- 本轮追「如何定义软件产品质量」。ISO/IEC 25010 的公开说明给出九个产品特性，并把质量定义为满足干系人显式与隐含需求的程度；功能适合性只是其中之一。出处：https://iso25000.com/en/iso-25000-standards/iso-25010 。采信其结论：需要结构化质量维度，但不照抄全部九类，而是按项目角色压缩为可检查底线。
- 未另找「Definition of Done」条目；其常见做法与 ISO 维度一致，记为假设：完成定义应包含质量约束，不只列功能。

## Options Considered

| Option | Cost | Risk | Reversibility | Time | Complexity |
|---|---|---|---|---|---|
| A. 只在完成判据里加“高质量” | 低 | 高：不可检查，审阅仍会按功能清单放行 | 高 | 0.5d | 低 |
| B. 结构化质量画像 + 固定三角色审阅 + 全链路验收引用 | 中 | 中：复杂档文案变长；若字段过重会拖慢 | 高：仅复杂档生效 | 2-3d | 中 |
| C. 独立全量评估平台，每次完整生成并跑端到端基准 | 高 | 中：验证周期长，容易把流程优化变成产品开发 | 中 | 1-2w | 高 |

**Recommendation: Option B**，因为它是能改变决策与实现行为的最小通用闭环。C 里的端到端验证保留为低频验收，不作为每轮修改 skill 的前置。

接受的取舍：

- 复杂 Goal 方案会比现在长一节；用固定小字段和“相关才写”限制膨胀。
- 三角色审阅增加一次派审成本；换回对产品、UI、工程偏差的早期发现。
- 不做自动质量评分器；先由角色审阅与人工证据判断，避免把主观 UX 变成假精确分数。

回退计划：逐个 patch 有 `proposal.md`、`change.patch`、`result.md`；回退时用历史 patch 还原生效行，保留任务台账作审计。

## Architecture

```text
┌──────────────┐    1. 样例原文    ┌────────────────┐
│ Benchmark In │ ───────────────▶ │ task-wizard     │
└──────────────┘                  │ 复杂档门禁      │
                                  └──────┬─────────┘
                                         │ 缺画像 → 完善中；缺确认降级 → P1
                                         ▼
                               ┌────────────────────┐
                               │ role-based-reviewer│
                               │ product/design/eng │
                               └──────┬─────────────┘
                                      │ P0/P1 写回方案
                                      ▼
┌──────────────┐   2. 画像/判据    ┌────────────────┐
│task-explore  │ ◀─────────────── │ decide→handoff │
└──────┬───────┘                  └────────────────┘
       │ 3. design 扩 UI/数据/验收；driver proposal 引用画像
       ▼
┌──────────────┐    4. 小切片实现  ┌────────────────┐
│taskflow      │ ───────────────▶ │ Delivery Slice │
└──────┬───────┘                  └──────┬─────────┘
       │        runtime + screenshot     │
       ▼                                 ▼
┌──────────────┐    5. 失败归类    ┌────────────────┐
│ Regression   │ ◀─────────────── │ Role Review    │
│ patch loop   │ ───────────────▶ │ skill patch    │
└──────────────┘                  └────────────────┘
```

- **Quality Profile**: 完成判据的可检查约束，固定六字段，复杂档必填。复杂档收编现有「交付标准」中的验证/测试、错误边界与运行假设；「交付标准」只写画像未覆盖的配套项，避免双清单。
- **Role Gate**: product 守范围与价值；design 守页面、状态、可用性与无障碍；engineer 守数据、错误、测试与启动。输出仍映射到 P0/P1/P2。
- **Propagation**: task-explore 不得在 decide/handoff 丢画像；taskflow 验收标准必须引用画像或写明无画像的原因。
- **Regression Loop**: 先跑一个窄切片，失败按 skill gap / implementation bug / acceptance gap 分类；skill gap 出 patch 后只重跑受影响切片。

## Interfaces

### Quality profile contract

```text
受众与场景: <谁在什么场景完成什么>
规模与运行假设: <人数、并发、数据量、本地/共享/生产>
页面/主流程: <3-7 条，每条有入口和结束状态>
角色底线:
  product: <核心工作流、范围外、协作边界>
  design: <视觉方向、关键状态、可用性/无障碍>
  engineer: <一致性、并发、错误边界、测试、启动证据>
显式降级:
  - 维度: <如数据库 / 实时协作 / 移动端>
    默认期望: <画像自然推出的要求>
    实际选择: <本次接受的实现>
    原因: <范围或约束>
    确认状态: <confirmed | pending>
```

### Review contract

```text
输入: 完成判据原文 + 质量画像原文 + 显式降级原文 + 该环节审/不审
模式: role-based-reviewer mode=review roles=product,design,engineer
输出: 每角色 findings；Blocker→P0，Major→P1，Minor→P2；统一完成程度
完成门: 画像字段齐、判据可检、核心底线有验证方式、pending 降级不存在
```

### Degradation confirmation

- 方案完善阶段一次列出所有已知生产性降级，初始状态一律 `pending`。
- `decide` 前将 pending 降级作为冻结门禁：必须由用户逐条确认后改 `confirmed`；goal 模式不把审阅收敛当作用户授权。
- 存在 pending 降级时状态改 `已停`，路由写「需要用户确认降级表」，不进入 handoff。
- 用户只说“继续”不算确认；必须点名接受的降级项或明确说“按降级表全部确认”。
- 实现中发现新的降级，先停在当前子 change 审阅，补入降级表并走同一确认门。

### taskflow acceptance

```markdown
## 验收标准
- [ ] <Goal 完成判据原文>
- [ ] 质量画像原文已进入 proposal；复杂任务缺画像时阻塞
- [ ] 每个角色底线至少有一条运行时、截图或测试证据
- [ ] pending 降级为 0；confirmed 降级在验证记录中可追踪
```

## State Management

- 质量画像的 source of truth 在 Goal 方案正文；`decide` 后交接必须带原文快照到 `TASK.md`、design 与 driver proposal。路径或小节指针只作辅助，不能替代快照。
- 降级状态只有 `pending` / `confirmed`；只有用户能改 `confirmed`。driver 中新增降级先 `pending`，回到同一确认门，不允许实现者或审阅者静默接受。
- 回归状态只记在任务台账和 `/tmp` 产物，不把本机结果写进共享 skill。

## Failure Modes

| Failure | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 画像写成空泛形容词 | 高 | 审阅仍放行 demo | 字段必须落到页面、状态、并发、测试、证据；写不出判为 P0 |
| 三角色意见重复或互相矛盾 | 中 | 修复优先级混乱 | 同一证据同一风险去重；分歧保留并按 P 级裁决 |
| 降级被改名为“技术选型”逃避确认 | 高 | 关键约束单方面放弃 | 按“比默认期望少交付”判定，不看措辞 |
| taskflow 子 change 丢失画像 | 中 | 实现者只看局部任务 | driver proposal 固定引用；缺失时子 change 不得开工 |
| 全量样例验证过慢 | 高 | 优化周期变长 | 先用 CRUD+看板窄切片；skill patch 后只重跑受影响切片 |
| 规则特例化成 task-manager 专用 | 中 | 无法开源复用 | 共享文案只用占位角色和通用样例；回归细节留任务目录 |

## Rollout / Migration

- Phase 1: task-wizard 增加复杂档硬指标、质量画像门、降级确认和固定三角色派审；同步 `task-wizard-goal` spec，并把“复杂档不触发质量门”列入回归反例。
- Phase 2: task-explore 与 taskflow 增加画像快照登记、交接与验收引用；role-based-reviewer 承认工作流调用；同步 `task-explore-lifecycle`、`taskflow-orchestration` 与 role reviewer 相关 spec/ADR，验收含“spec 已同步”。
- Phase 3: 建通用小切片回归包：固定样例原文、可检查 rubric、窄切片步骤和证据清单；先跑一次，失败驱动 patch。
- Phase 4: 全量实现或再收敛；每轮只跑受影响切片，最后跑一次全链路验收。

## Regression acceptance

单切片验收按 0-3 分记录，证据必须落 `/tmp/agent-delivery-quality/`：

| 维度 | 3 分 | 2 分 | 通过线 |
|---|---|---|---|
| 功能闭环 | 主流程全通，失败路径可用 | 主流程通但有未处理边界 | ≥2 |
| UI/UX | 信息架构、视觉层级、关键状态、反馈、无障碍、响应式均可检查 | 可用但个别子项不足 | ≥2 且无 0 分子项 |
| 工程质量 | 测试、错误边界、启动说明齐 | 测试或启动说明有缺口 | ≥2 |
| 画像一致性 | 实现逐条对得上画像 | 有已确认且记录的降级 | 无未确认偏差 |
| 证据 | 运行时截图/导出日志 + 命令可复现 | 证据部分缺失 | 全部齐 |

评分主体与顺序：先交证据，再由 role gate 对应角色打分——product 评功能闭环与画像一致，design 评 UI/UX，engineer 评工程质量；实现 agent 自评只作输入，不算通过线。UI/UX 单切片得分是信息架构、视觉层级、关键状态、操作反馈、无障碍、响应式六个子项的平均分，每个子项不得为 0。

窄切片周期目标：从干净 `/tmp` 工作区到评审证据齐备不超过 2 小时；超过即把缺口拆成 skill gap 或 implementation bug，不继续堆工作量。全量通过线：5 个维度均 ≥2 且 UI/UX 平均 ≥2.5；若目标是“优秀 UI/UX”，设计底线逐条通过且截图评审无 Major。

## Open Questions

- [x] 质量画像的最小字段 —— 采用 ADR 中的六字段。
- [x] 复杂档如何不拖慢 —— 仅复杂档强制，字段最多 3-7 条主流程。
- [x] 回归如何提速 —— 窄切片先行、失败分类、patch 后只重跑受影响切片。
- [ ] 窄切片回归包第一轮选哪些页面 —— 推荐“登录/任务列表 + 看板拖拽 + 任务详情评论”；待 decide。
- [ ] qoder 与 qwen 3.8 flash 的具体名册 Endpoint —— 实现/对照轮用 `agent-roster` 查询；名册不可用则停，不假名。

## Cross-References

- **Task doc**: `../TASK.md`
- **Skill sources**: `agents/skills/task-wizard/`, `agents/skills/task-explore/`, `agents/skills/taskflow/`, `agents/skills/role-based-reviewer/`
- **Specs**: `openspec/specs/task-wizard-goal/spec.md`, `openspec/specs/task-explore-lifecycle/spec.md`, `openspec/specs/taskflow-orchestration/spec.md`
- **Downstream**: `decide` → `handoff`；实现通过 taskflow driver 与 skill-upgrader patches 执行。
