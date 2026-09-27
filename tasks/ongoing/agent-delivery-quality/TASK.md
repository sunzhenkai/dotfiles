# Agent 交付质量门缺失（task-manager 复盘）

- slug: agent-delivery-quality
- status: handed-off
- created: 2026-09-25
- updated: 2026-09-27
- handed-off: 2026-09-27

## 目标

- 让 Agent 的交付流程不再系统性产出「功能齐但 demo 化」的成品：完成判据必须引用质量画像，审阅必须带岗位角色，生产性降级取舍必须显式由用户确认。

## 非目标

- 不重做 /home/wii/tmp/task-manager 那版 task 平台（它的价值是回归案例，不是交付对象）。
- 不改 task-explore 的生命周期状态机、不改 taskflow 的编排协议。
- 不引入「每个任务都必须上生产级基础设施」的硬性要求。

## 现状

- 上一版实现现场：`/home/wii/tmp/task-manager`。后端 708 行 Python（FastAPI + SQLAlchemy + SQLite，后台 6 个 router），测试 4 个文件；`frontend/` 只剩 `package.json`、`vite.config.ts`、`tsconfig.json` 三个文件，**没有任何 React 源码**。交付仓无 commit。
- 上一版台账：`/home/wii/tmp/task-manager/tasks/ongoing/task-platform/TASK.md`（status: handed-off）与 `design/platform-design.md`。判据原文与方案原文已在其中。
- 上一版判据原文：在 `/home/wii/tmp/task-manager` 交付可本地启动的平台，支持成员登录、创建/更新/关闭 task、看板视图、评论、状态/成员/项目筛选、项目/成员分配、审计时间戳；配套种子数据、README、自动化验收与单元/集成测试全绿，并用运行时截图或导出日志证明核心流程可用。
- 关键事实：该判据的每个子句都是布尔功能项，没有任何质量维度（UI 水平、数据层生产性、并发假设）。判据里的「看板视图」被当作功能动词满足。
- 关键事实：`design/platform-design.md` 里 SQLite 是**显式写下的取舍**（「接受 SQLite 单机单进程 + WAL」），不是漏想；问题在于它由 agent 单方面宣布，未征询用户。
- 关键事实：同一次交付的审阅只提了「单元测试无归属步骤」这类形式问题并给出「高」完成度——因为派审提示词把审阅面锁死在判据内。
- 相关流程资产（都在本仓）：`agents/skills/task-wizard/`（含 15 个 patches、`CONTEXT.md`）、`agents/skills/task-explore/`、`agents/skills/role-based-reviewer/`；`openspec/specs/task-wizard-goal/spec.md`、`openspec/specs/task-explore-lifecycle/spec.md`。
- 本机已有但上一轮完全没被挂进流程的 UI 能力：`ui-skills-root`、`pretty-view-html/references/frontend-design`。
- 背景澄清：今天早些时候的 patch `20260925-065234-delivery-standard` 已针对「demo 化」加过一轮「交付标准」小节，但那一节只覆盖验证/测试、错误边界、文档配置三类工程卫生，**不含产品与设计质量**，且允许「不确定的维度写进『不做的事』」，因此并未堵住本次失败。

## 方案

- 完成判据：产出并落地一组 skill 改动，使得 (1) task-wizard 复杂档的完成判据必须引用质量画像，写不出即阻塞；(2) 复杂档审阅强制含 product/design/engineer 角色；(3) 所有生产性降级取舍必须显式由用户确认；(4) 用 task-manager 这次失败作为回归案例，验证新流程在同样输入下能产出含 UI 规格与生产选型确认的方案。
- 事实：如上「现状」。用户已在 explore 第一轮确认 Q1–Q8 的推荐答案（改流程为主、任务落 dotfiles 仓、判据引用质量画像、复杂档不跳 explore、降级必须确认、UI 走已有 ui skill + 规格截图、审阅加 engineer、判据即上述骨架）。
- 假设：`ui-skills-root` 的具体可选类别未实跑（依赖 npx 在线拉包）；若实跑发现没有合适类别，退回 `frontend-design` 单走，不阻塞方案。
- 假设：taskflow 的 proposal 模板具体改动位置（在「验收标准」小节加引用行）尚未读模板原文确认，design 阶段核对。
- 步骤：待 design 阶段细化。
- 阻塞点：无。
- 坑：本任务改动落在 `agents/skills/`，必须走 `pwd-skill-manager` → skill-upgrader 的 patches 协议，不能直接手改 SKILL.md。
- 坑：`role-based-reviewer` 门 1 的改动要同时改它自己的 SKILL.md 与本仓 `openspec/specs/` 中相关条目，否则两处说法会分叉。
- 坑：本仓工作区当前已有未提交改动（`agents/runtime.yaml`、`agents/skills/task-wizard/SKILL.md`、`references/legacy-plans.md` 与两个未应用的 patches 目录），本轮改动叠加前要确认这些改动如何处置。

## 进展

- 2026-09-25：立项。根因初判 R1–R4（判据缺质量维度 / 交付标准只含工程卫生 / 审阅不带角色 / 缺前置正向设计）。第一轮 8 问按推荐确定。下一步 explore。
- 2026-09-25：explore 第二轮 8 问按推荐确定（Q9–Q16）：质量画像为 Goal 方案内结构化小节（受众/规模/生效角色/各角色底线，角色词表借 role-based-reviewer 的 9 角色）；只复杂档强制画像；改 role-based-reviewer 门 1 承认「task-wizard 复杂档调用」为正当触发；降级项交审阅者判「理由是否正当」；UI 规格 = 页面清单 + 三条角色底线，截图存 /tmp；回归案例同时落任务目录与 skill-evolver examples 格式；改动面 = task-wizard + task-explore（taskflow/openspec 不动）；本仓同步 spec + ADR + patches + CONTEXT.md 术语。
- 2026-09-25：explore 第三轮 4 问按推荐确定（Q17–Q20），frontier 已空。**Q17 修正了第一轮的一处事实错误**：`ui-skills-root` 是路由层（`npx ui-skills start/categories/list/get`，vercel-labs），`frontend-design` 是本仓 `pretty-view-html/references/` 下的参考文档，两者不同层——挂法改为先 `frontend-design` 定方向、再 `ui-skills-root` 按方向选窄 skill，`npx` 不可用时退回 `frontend-design` 单走。Q18：taskflow proposal 模板加一行引用质量画像。Q19：回溯验证取「读新 skill 文本 + 对照失败点清单」，不实跑。Q20：本任务走完整 design → decide → handoff → taskflow 流程。
- 2026-09-27：driver 规划完成并交接。wizard、explore/taskflow/reviewer 传播链、静态回归包均已落地；`make registry validate`、secret-scan、`pytest` 1041 passed，OpenSpec strict 校验通过。
- 2026-09-27：通用闭环已上移 taskflow：小切片回归、验收 rubric、实现者输入双模式（正常交付 / 盲测复跑）。任务目录只保留案例证据与决策过程。
- 2026-09-27：样例完成 final polish 并通过最终三角色验收：260/260 tests OK，五维 3.0，UI/UX 3.0，明暗对比 62/62 达标，无 P0/P1；生产部署 checklist 已写入 README/降级表。
- 2026-09-27：样例窄切片已由 qodercn 实现并返修。首轮 100/100 tests；三角色审阅后修复安全、事务、会话身份、force 审计与 500 泄漏；复核 142/142 tests OK，无 P0。剩余 UI/UX 1.92 未达 2、3 个共享部署前 P1、全链路功能扩展未做。采纳 ISO/IEC 25010 的结构化质量维度思路，并压缩为六字段质量画像；定义复杂档硬指标、pending 降级用户确认门、原文快照传递、三角色评分与小切片回归。第一轮审阅 4 个 Major；修订后逐条复核全部消失，无新 P0/P1，完成程度高。

## 决策

- D1 采纳：方案 B「结构化质量画像 + 固定三角色审阅 + 全链路验收引用」——它是最小通用闭环，能改变方案、审阅与实现行为，而不把流程优化变成全量评估平台。
- D1 取舍：接受复杂 Goal 方案多一节质量画像和三角色审阅成本；接受先不做自动质量评分器。放弃「只加高质量形容词」与每轮全量端到端验证。
- D1 带进实现的未决：
  - 窄切片回归包第一轮选「登录/任务列表 + 看板拖拽 + 任务详情评论」；如样例能力边界不同，可在实现期按同一原则换 3 个核心闭环，但需在 proposal 说明。
  - qoder 与 qwen 3.8 flash 的具体 Endpoint 用 `agent-roster` 查询；名册不可用则停，不假名。
- D1 回退：按各目标 skill 的 patch 目录回退生效行；保留本任务台账与 `/tmp` 回归证据作审计。

## 交接

- driver: `agent-delivery-quality-driver`
- 采纳方案: D1 方案 B「结构化质量画像 + 固定三角色审阅 + 全链路验收引用」
- design: `design/delivery-quality-loop.md`；契约见 `design/adr-quality-profile.md`
- 可带进实现的未决:
  - 窄切片首选「登录/任务列表 + 看板拖拽 + 任务详情评论」；能力边界不同时可换 3 个核心闭环，但须在 proposal 说明。
  - qoder 与 qwen 3.8 flash 的 Endpoint 由 `agent-roster` 查询；名册不可用则停，不假名。
- proposal: `openspec/changes/agent-delivery-quality-driver/proposal.md`

## 未决问题

- [x] ui-skills-root 与 frontend-design 的先后关系 —— Q17
- [x] taskflow driver 的验收标准模板 —— Q18
- [x] 本任务完成判据是否加回溯验证 —— Q19
- [x] 质量画像的具体形态 —— Q9
- [x] 与 role-based-reviewer 门 1 的冲突 —— Q11
- [x] 回归案例如何固化 —— Q14
- [x] 生产性降级的显式确认 —— Q12
- [x] UI 规格与截图对照 —— Q13

## 下一步

- driver 与子 change 已归档，交付验收通过；如需把探索任务移入 archive，再点名 `archive agent-delivery-quality`。
