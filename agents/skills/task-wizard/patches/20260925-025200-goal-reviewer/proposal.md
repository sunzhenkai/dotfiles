# Goal 方案由审阅者把关，只有高置信度才继续

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-025200-goal-reviewer
- risk: high
- status: proposed

## Intent

处在 goal 里时，Goal 方案写完、改代码之前必须经审阅者。审阅者只读，返回方案置信度、每个决策点一条建议、缺陷。方案置信度为高时，建议写入步骤并按档位继续。中停在「方案置信度不足」，低停在「理解不够」，都不改步骤。「仍按此方案执行」只放行当前步骤这份方案。

默认审阅者是当前宿主里更强模型的子 agent；当前已是最强档时另起同模型子 agent。goal 原文或当轮消息写了 `agent-roster` 才委托 `$agent-roster`。名册派不出就停，不改回子 agent。

方案置信度为高且档位为中等时，直接 `openspec-propose` 再 `openspec-apply-change`，拷问由审阅者完成。复杂档仍等用户说走 task-explore。

非目标：不改任务方案的确认与 grill；不改 task-explore 内部的人选和确认冻结；不把 skill 改成自进化；不落方案文件；不自动 sync、commit 或 push。

## Conflict check

- 任务方案「先拷问后实现」与 Goal 中等档冲突。处理：该条仍只约束任务方案。Goal 中等档的拷问由审阅者完成，衔接从 `openspec-propose` 开始。
- 原「理解不够」含「两个以上会改步骤的理解」。处理：判据写得出来但步骤或验证站不住，改为退出点「方案置信度不足」；「理解不够」留给写不出判据，或步骤主体靠猜测。
- `$agent-roster` 的候选表与等人安装会把无人值守的 goal 停死。处理：只在 goal 原文或当轮消息点名时委派；不列候选表；派不出用「审阅派不出」，不退回本机子 agent。不复制其契约。
- 公开 skill 的新段落不写仓库专属安装命令，沿用 Goal 节已有的「给出安装选项」。

## Rationale

goal 没有人盯着。建议若只是参考，执行会停在每个决策点；中、低把握也继续，执行者会把站不住的计划自己修到能开工。用户已逐条确认该契约。

## Files

- agents/skills/task-wizard/SKILL.md — Goal 方案增加审阅顺序、置信度门禁、放行句，并改写中等路由
- agents/skills/task-wizard/CONTEXT.md — 决策点、审阅者、建议、方案置信度及相关退出点

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；任务方案的 grill 衔接仍在；Goal 节含审阅、方案置信度三档、中等档直接 OpenSpec、复杂档仍等 task-explore
