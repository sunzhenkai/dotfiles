# Goal 里向用户确认的决定都走审阅

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-064335-goal-confirm-via-review
- risk: high
- status: proposed

## Intent

处在 goal 里时，凡要向用户确认的决定，含路由选择和下游 skill 里的确认，都走「审阅」，不列选项。审阅收敛则采纳推荐默认并继续。创建目录、选阶段、确认冻结、脏工作区选择不再留给下游自己问人；冻结在审阅收敛后即 `decide` 并 `handoff`。

排查写不出步骤时，推荐走 task-explore，先审阅，收敛后直接开始。详细设计，以及危险操作、线上动作、泄密，仍停，不交给审阅放行。

非目标：不改任务方案的确认；不改审阅的 P0/P1 核对循环；不改 task-explore 的非 goal 确认。

## Conflict check

与上一轮「下游确认仍按 task-explore 自己的门禁」冲突，本 patch 取代该条。与「审阅收敛才进入写完之后」一致：这里的审阅是同一套完成程度与 P0/P1，用来放行原本要问用户的那一条决定。

## Rationale

只改 task-wizard 的路由句、不改下游，执行者读到 task-explore 仍会弹出选择。只改下游、wizard 仍写「按下游门禁」，两份契约会打架。用户已点名 goal 里的确认都走评审。授权门禁会改变 agent 行为，风险为 high；确认的是该契约。

## Files

- agents/skills/task-wizard/SKILL.md：Goal 确认走审阅；排查改为先审阅；复杂档路由不再把冻结确认留给用户

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 task-wizard；复杂路由不再写「按 task-explore 自己的门禁」
