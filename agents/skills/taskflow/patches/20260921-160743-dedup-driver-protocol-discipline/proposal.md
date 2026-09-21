# 去重 Driver 协议与纪律小节（writing-for-agents 优化）

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-160743-dedup-driver-protocol-discipline
- risk: medium
- status: proposed

## Intent

按 writing-for-agents 的「单一真相源」原则消除正文重复，不改变任何行为：

1. `纪律 / 涉及面与交付分支`：切分支规则与 Driver 协议模板（逐字写入每个 driver proposal 的固定文本）重复且措辞已漂移。模板是被 eval case `driver-protocol-verbatim` 钉死的拷贝源，必须保留全文；故纪律小节降级为「指向模板 + 模板未写的增量（已准备成功的仓保留现状）」。
2. `纪律 / 一轮结束`：同上，三条件与处置规则在模板中已有；纪律小节只留增量（不勾假完成、不按 change 汇总数量、不因一项卡住整轮停下）。
3. frontmatter `description`：删去「独立子 change 与独立 task 在有多 agent 时并行 apply」——这是能力陈述不是触发分支，正文已承载，常驻 context 不应为其付费。

非目标：不动 Driver 协议模板逐字文本；不动脚手架、propose 骨架、委托契约、并行执行、Self-evolution 注入块；不改变任何行为规范。

## Conflict check

- evals/cases.yaml 的 `driver-protocol-verbatim` / `fail-closed-must-repos` / `round-end-three-only` 等 case 所要求的内容仍全部存在于 SKILL.md（模板 + 增量），无冲突。
- task-explore 的 `references/phase-handoff.md` 引用 taskflow 的脚手架与逐字 Driver 协议，未触及。
- Self-evolution 注入块为 skill-upgrader 标准件，有意不裁剪（保持幂等检查与跨 skill 一致性）。

## Rationale

重复规则已实际漂移并被迫双处维护（见本轮之前 20260921-154244、20260921-155458 两个 patch 均同时改动模板与纪律小节）。收敛为单一真相源后，后续规则调整只需改模板一处。行为不变，可由既有 eval cases 逐项核对验证。

## Files

- agents/skills/taskflow/SKILL.md — description 删一句；纪律两小节改写为「指针 + 增量」

## Validation

- 应用前：`git apply --check --recount`（已通过）
- 应用后：`git diff --check`；人工逐项核对 evals/cases.yaml 全部 14 个 case 的 must / must_not 仍被 SKILL.md 文本覆盖；frontmatter `name` 与目录名一致
