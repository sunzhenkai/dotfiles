# 新增可选 plan-review 阶段：decide 前用 $agent-roster 评审方案

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-022440-add-plan-review-phase
- risk: medium
- status: proposed

## Intent

`design` 产出方案后直接进 `decide` 冻结，中间没有独立评审关口。想让方案在冻结前被另一个 agent 看一遍，目前没有阶段可落。

改动：在 `design` 与 `decide` 之间加**可选**阶段 `plan-review`，直接委托 `$agent-roster`（单次评审委派，不走 `$agent-roster-flow`）：

1. 新增 `references/phase-plan-review.md`：门禁（已有方案稿、工作树干净）、按 `$agent-roster` 路由、把候选收成编号表让用户选、`read-only` 委派、回收意见落 `{taskRoot}/design/review-<date>.md`、按意见回 `design` 修正、失败分类与留痕交给 `$agent-roster`。
2. `SKILL.md` 阶段表加 `plan-review` 行，并在 `design` 行标注其产出是 `plan-review` 的入口。
3. `SKILL.md`「加载」表加 `plan-review` → `references/phase-plan-review.md`。
4. `SKILL.md` 正文加 `## `plan-review`` 小节，标明可选、在 `design` 与 `decide` 之间、先读该 reference。
5. `design` / `decide` 小节各加一句指路：design 完成后可走 plan-review，decide 无可评审方案/未评审不阻断。

非目标：不改 `handoff` / `archive` / `reopen` / `split` / `new` / `save` / `explore`；不改 `INDEX.md`（本阶段不写 INDEX，除非用户同时 save）；不改子任务机制；不改落点约束（评审产物仍在 `{taskRoot}/design/`）。

## Conflict check

- 公开性：`agents/skills/` 面向公开复用。`$agent-roster` 是用户级 Skill，不在本仓 `agents/skills/` 下；本仓已有 `task-wizard` / `taskflow` 互相按 `$name` 引用同源外部 Skill 的先例，本次沿用同一形态（`$agent-roster`，不写安装路径、不写 `~/.agents`）。
- 与 `phase-design.md` 不重叠：design 产出方案与推荐，plan-review 只读评审并回 design 改稿；评审不写决策。
- 与 `phase-decide.md` 不重叠：decide 冻结采纳；plan-review 是可选的、不阻断 decide 的前置顾问步。
- 与 `phase-handoff.md` 不重叠：handoff 才交接 taskflow；plan-review 不建 driver、不归档。
- `agent-roster` 已有 `human` 作为评审 Assignment 的口径（见 `agent-roster-flow` 的 `plan-review` Stage），本阶段允许「用户/同事已评审」直接算完成。

## Rationale

按 writing-for-agents：可选分支该按需披露。评审步骤只在有方案、且用户想借外力时才走，放独立 `references/phase-plan-review.md` 并在加载表按需读取，避免所有 run 都背这段上下文。委派细节单一真相源在 `$agent-roster`，本阶段只写「何时触发 / 产出落哪 / 怎么衔接」，不复制契约字段与 acpx 用法。

## Files

- agents/skills/task-explore/references/phase-plan-review.md — 新增（可选阶段正文）
- agents/skills/task-explore/SKILL.md — 阶段表 + 加载表 + 新增 `## plan-review` 小节 + design/decide 指路

## Validation

- 应用前：`git apply --check --recount`（目标通过）
- 应用后：`git diff --check -- agents/skills/task-explore`；`python3 agents/skills/task-explore/tests/test_task_explore_contract.py` 全绿；frontmatter `name` 与目录名一致
