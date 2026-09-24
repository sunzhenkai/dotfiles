# 审阅为低或中时进入完善，不再当作退出

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-051644-review-refine-not-exit
- risk: high
- status: proposed

## Intent

Goal 方案审阅档位为低或中时，进入完善：把本轮建议写入完成判据与步骤，同一轮再审。档位本身不再是退出点，不向用户索取「仍按此方案执行」或「按审阅建议改方案」。只有高且无缺陷才进入「写完之后」。完善期间不改代码。

同一缺陷写入后再审仍在，才用退出点「审阅不通过」（换一种说法仍指同一处缺口，算同一条）。完善之后仍写不出可检查的完成判据，才用「理解不够」。审阅档位为低本身不用这个标签。

已因中或低而 `已停` 的旧方案：不再等待授权，改为完善后再审。

非目标：不改任务方案的 grill 衔接；不改复杂档的 task-explore 门；不改线上动作、泄密、危险操作等其余退出点；不把完善期间的改正放进实现。

## Conflict check

与 `20260925-025200-goal-reviewer` 冲突：该轮把中定为退出点「方案置信度不足」、低定为「理解不够」，且中或低不改步骤。本轮删掉「方案置信度不足」这个退出点，低或中改为完善的输入。高且无缺陷才开工仍然保留，避免把站不住的方案直接拿去改代码。

`docs/adr/0025` 与 `openspec/specs/task-wizard-goal/spec.md` 仍写着旧退出。二者不在本 patch 路径内，应用后另改，使契约与正文一致。

## Rationale

审阅给出可执行建议时，停下来等人二选一不会增加信息，只是把完善阶段做成退出。完善只改方案并再审；开工门仍是高且无缺陷。同一缺陷再审仍在才停，避免把中档自己谈成高后开工。

用户已点名该行为：评审为低、中时应继续完善，属于不必要的退出。高风险门禁按此具体行为视为通过。

## Files

- agents/skills/task-wizard/SKILL.md — 完善阶段、档位规则、旧方案回续、退出点
- agents/skills/task-wizard/CONTEXT.md — 完善术语；方案置信度与理解不够不再把低或中定义为退出

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；正文不再把中或低写成 `已停`；低或中指向完善；「方案置信度不足」不再作为退出点出现在 `SKILL.md`；无本 skill 测试
