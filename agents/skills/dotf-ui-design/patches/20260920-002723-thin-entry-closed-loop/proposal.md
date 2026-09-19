# 入口做薄 + 流程闭环：SKILL.md 收为路由器，模式细节下沉 modes/，闭环协议独立 plans.md

- target: agents/skills/dotf-ui-design
- mode: update
- patch: 20260920-002723-thin-entry-closed-loop
- risk: medium
- status: proposed

## Intent

把入口 `SKILL.md` 从 100 行的"路由 + 三模式摘要 + 落盘协议"收成 ≤50 行的纯路由器（frontmatter description 一字不瘦，保留全部触发关键词）；三模式流程分别下沉到 `references/modes/{design,audit,motion}.md`，选定模式后才加载，降低上下文成本并消除与 vendor 摘要的双写漂移。

同时把开环的"审计 → 计划"补成闭环：新增 `references/plans.md`，定义计划落盘、状态机（TODO → IN_PROGRESS → DONE / BLOCKED / RETIRED）、priority 统一映射（motion severity 与 audit confidence×impact 都归一到 P0/P1/P2）、执行承接协议（计划为唯一规格、drift 停报、验证回执）与 reconcile 回流（verify 未过 → 回流 audit 重新取证）。

行为变化点（相对现状）：

1. modes/motion.md 增加 override：屏蔽 vendor 的 bare 调用问候语；计划目录统一 `design-plans/`（vendor 写 `plans/`）；禁用 vendor 的 `execute <plan>` 变体，执行统一走 plans.md 承接协议。
2. modes/audit.md 增加 override：索引用 priority（vendor 只有 Confidence）；quick 档位仍最多 3 条（与 motion quick 约 5 条分开声明，消除原入口的矛盾）。
3. modes/design.md 增加第 0 步 recon（定位 surface、既有设计系统约束、验证方式）与闭环出口（建议 audit 验收）。
4. commit 戳可降级：非 Git 环境写 `unavailable` 并记录日期（原入口强制取 SHA，与 audit 模板允许 unavailable 不一致）。

非目标：不改 vendor 三个上游文件一个字节；不改 sources.yaml；不加 examples/evals（等真实执行经验）；不补 MIT LICENSE（另行处理）。

## Conflict check

- frontmatter `description` 保持不变，触发面不变。
- vendor improve-animations 的 `execute <plan>` 与 bare 问候语被 override——这是本 patch 的核心意图（入口已接管路由与执行承接），已在 modes/motion.md 用 override 表显式声明"以本 skill 为准"，与入口"流程文件与 vendor 冲突时以流程文件为准"一致。
- 与其他 Skill 无职责冲突：不替代设计系统治理流程（入口保留"不另造组件体系"边界）。

## Rationale

- 入口摘要是 vendor 流程的双写，上游更新后必然漂移；下沉后 modes/* 只留骨架 + override，vendor 仍是唯一细节来源。
- 现流程在"计划写完"处断开：无状态、无回执、无退役，README 索引要求的 severity 在 audit 模板中不存在。plans.md 用一份协议补齐闭环，且对执行者模型能力无要求（计划自包含原则不变）。
- 可验证：应用后入口行数 ≤50；modes/* 与 plans.md 引用路径全部存在；vendor 文件零改动（git diff 可证）。

## Files

- `agents/skills/dotf-ui-design/SKILL.md`（改写：收薄为路由器，保留 frontmatter 与信条、路由判断、跨模式硬边界、vendor 治理段）
- `agents/skills/dotf-ui-design/references/modes/design.md`（新增：recon + 定题 + 两遍法 + 实现 + 自评与闭环出口，品味内核要点并入）
- `agents/skills/dotf-ui-design/references/modes/audit.md`（新增：六步骨架 + override 表 + 品味来源指针）
- `agents/skills/dotf-ui-design/references/modes/motion.md`（新增：四步骨架 + override 表 + 数值来源约束）
- `agents/skills/dotf-ui-design/references/plans.md`（新增：落盘、状态机与台账、priority 映射、执行承接、reconcile 闭环）

## Validation

- 应用前：`git apply --check --recount`。
- 应用后：`git diff --check -- agents/skills/dotf-ui-design`；确认 vendor 三目录零改动（`git status` 仅列上述 5 个文件）；入口 SKILL.md ≤50 行；modes/* 与 plans.md 中所有相对链接目标存在；frontmatter id/name 与目录名一致；无隐私信息。
