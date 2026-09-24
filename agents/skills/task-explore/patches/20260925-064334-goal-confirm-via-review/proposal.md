# Goal 里的确认改走审阅

- target: agents/skills/task-explore
- mode: update
- patch: 20260925-064334-goal-confirm-via-review
- risk: high
- status: proposed

## Intent

处在 goal 里时，本 skill 里要向用户确认、选择或询问的决定改为走 task-wizard 的「审阅」，不列选项。推荐默认是该处已写出的默认。审阅收敛则视为已确认并继续。冻结未决并交接时，收敛即本轮 `decide` 完立刻 `handoff`。

不在 goal 里时，原确认规则不变。目标已存在仍禁止覆盖，不交给审阅放行。task-wizard 读不到时停并给出安装选项，不改回问用户。

非目标：不改阶段顺序；不改父任务禁止 handoff；不改 ledger 写纪律；不把 skill 改成自进化。

## Conflict check

与「未决须逐条经用户确认」「没有 tasks/ 须先确认再创建」等句冲突的，只在处在 goal 里时。这些句子保留给非 goal。与 task-wizard 的审阅（完成程度、P0/P1）一致，不另写一套评审。

## Rationale

Goal 里再弹出「全部按默认冻结并交接 / 先改某条 / 暂不冻结」不增加信息。推荐默认已经写在 design 里，应由审阅判断它能否让完成判据成立。用户已点名：goal 模式下所有需要用户确认的都走评审。确认门禁会改变 agent 行为，风险为 high；确认的是该契约。

## Files

- agents/skills/task-explore/SKILL.md：增加「Goal 里的确认」，decide 在 goal 里改走审阅
- agents/skills/task-explore/references/phase-decide.md：goal 里不列冻结选项，审阅收敛后写入并 handoff
- agents/skills/task-explore/references/phase-handoff.md：goal 里不询问是否交接
- agents/skills/task-explore/tests/test_task_explore_contract.py：锁定上述句子，并保留非 goal 的逐条确认

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；`python3 -m unittest tests.test_task_explore_contract`；frontmatter `name` 仍为 task-explore
