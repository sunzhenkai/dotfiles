# task-wizard 识别被上游 skill 以 goal 模式委派的调用

- target: agents/skills/task-wizard
- mode: update
- patch: 20260927-183940-goal-delegation-detect
- risk: high
- status: proposed

## Intent

- 分流判定新增第三种命中：被上游 skill（如 delivery-loop）以 goal 模式委派调用时，同样进入「Goal 方案」分支。
- 非目标：不改变 Goal 方案正文、审阅、退出点与档位路由；不改变任务方案分支。

## Conflict check

- 现有判定是「消息里看得到 `/goal`，或进行中的 goal 且本条消息挂了本 skill」；被 delivery-loop 间接调用时是否算「挂了本 skill」存在歧义，本改动消歧，与 delivery-loop 的 goal 模式互为呼应，无冲突。

## Rationale

delivery-loop 的 goal 模式需要 task-wizard 明确进入 Goal 方案分支；在分流判定里显式写明委派调用，避免依赖「挂了本 skill」的模糊解释。通用表述不绑定单一调用方。

## Files

- agents/skills/task-wizard/SKILL.md：frontmatter description、先分流 Goal 方案判定句。

## Validation

- `git apply --check --recount` 通过。
- 应用后 `git diff --check` 无空白错误；与 delivery-loop 的 goal 自动识别句对照无矛盾。
