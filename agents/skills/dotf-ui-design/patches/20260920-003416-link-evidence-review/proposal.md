# 衔接 visual-evidence 与 dotf-ui-review：取证、验收、设计系统缺位转介

- target: agents/skills/dotf-ui-design
- mode: update
- patch: 20260920-003416-link-evidence-review
- risk: medium
- status: proposed

## Intent

闭环补齐的第二轮：把新创建的配套 skill 接入三模式与 plans 协议。

1. **取证衔接**：design 自评截图、audit 的 rendered evidence（用户要求视觉检查时）、motion 的 feel check（慢放 / reduced-motion 对比）统一指向 visual-evidence 流程，全部带"若环境中可用"降级。
2. **独立验收衔接**：plans.md 执行承接允许委托 dotf-ui-review 做 diff 级验收，verdict 报告作为验证回执附件；design 闭环出口同样可选委托。
3. **设计系统缺位转介**（audit 新增行为）：反复因缺契约证据证不成 finding 时，停止审计而非放宽证明标准——候选记为"待契约"清单，建议先沉淀项目设计系统（DESIGN.md / token 体系；环境中有治理类 skill 如 ui-template-design 可转介），契约就位后恢复审计。

非目标：不改 vendor；不改路由与状态机；不引入对配套 skill 的硬依赖（全部"若可用"降级）。

## Conflict check

- 与 vendor improve-ui "Use rendered evidence only when the user provides it or explicitly requests visual inspection" 不冲突：本 patch 只在用户要求视觉检查时定义取证方式，不扩大取证触发面。
- 设计系统缺位转介与 audit "宁要没有 finding" 的立场一致：是停止条件的显式化，不是新增 finding 来源。
- 配套 skill 均为同编目公开共享 skill，引用带降级，不写死仓库布局。

## Rationale

- 取证方式此前只有"环境支持就截图"一句话，三处各自即兴、证据不可复验；统一指向 visual-evidence 后，finding 与回执的证据引用格式一致。
- 执行者自查不是独立验收；dotf-ui-review 提供第二双眼睛，verdict 直接挂进现有回执字段，不改状态机。
- 无设计系统的项目里 audit 的契约证成必然频繁失败，显式转介比反复空转审计更符合"宁要没有 finding"。

## Files

- `agents/skills/dotf-ui-design/SKILL.md`（新增"配套能力"小节）
- `agents/skills/dotf-ui-design/references/modes/design.md`（自评取证 + 闭环出口委托验收）
- `agents/skills/dotf-ui-design/references/modes/audit.md`（override 表加取证方式行；新增"设计系统缺位"段）
- `agents/skills/dotf-ui-design/references/modes/motion.md`（override 表加 feel check 取证行）
- `agents/skills/dotf-ui-design/references/plans.md`（执行承接加取证与独立验收）

## Validation

- 应用前：`git apply --check --recount`。
- 应用后：`git diff --check`；改动仅限声明的 5 个文件；所有"若环境中可用"降级措辞到位；无隐私信息。
