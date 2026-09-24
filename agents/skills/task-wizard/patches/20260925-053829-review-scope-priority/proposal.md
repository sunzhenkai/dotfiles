# 审阅按环节限定范围，通过只看完成程度

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-053829-review-scope-priority
- risk: medium
- status: proposed

## Intent

Goal 方案每次派审把该环节的审阅范围原样交给审阅者。步骤确定只审大体步骤；执行中的新决策点只审这条岔路和尚未验证的步骤；已交接后只审尚未开始的步骤。范围内意见分 P0、P1、P2。P0 与 P1 必须解决，本轮有它们时完成程度取中或低，写入后再审。只剩 P2 时写入方案，完成程度为高则评审收敛。评审阶段是否通过只看完成程度是否为高。

触发：处在 goal 里写完方案、执行中出现新决策点、已交接后出现新决策点。非目标：不改任务方案的 grill 衔接；不改三档路由；不让审阅者写详细设计；不把简单和中等的每一轮都做成外部参照。

## Conflict check

与 `20260925-052211-review-suggest-loop` 冲突：该轮把开工门放在改进意见「已达到预期」。本轮改为完成程度为高，且本轮没有 P0、P1，P2 已写入。低或中仍进入完善、不改代码，与 `20260925-051644-review-refine-not-exit` 一致。任务方案仍不叫审阅者。

## Rationale

不划范围时，步骤确定阶段会被要求补架构、接口或代码骨架。不分级时，必须改的和可以后补的混在同一轮，方案要等一句「已达到预期」才定稿。P0、P1 挡住「高」；只剩 P2 且完成程度为高即可收敛。

## Files

- agents/skills/task-wizard/SKILL.md — 三档审阅范围、P0/P1/P2、评审收敛
- agents/skills/task-wizard/CONTEXT.md — 审阅范围、完成程度、P0、P1、P2、评审收敛

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；正文含三档审阅范围与「评审收敛」；开工门不再是「已达到预期」；无本 skill 测试
