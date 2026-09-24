# Goal 收敛后按档位直接下一跳，不再索取路由确认

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-063810-goal-skip-route-confirm
- risk: high
- status: proposed

## Intent

处在 goal 里、评审已收敛时，复杂档不再停成 `已停` 等用户说「走 task-explore」，也不列出「走 task-explore / 仍按此方案执行」二选一。「仍按此方案执行」只在完善期间由用户主动说出时停完善，不得解释成在本会话按步骤改代码。

简单、中等、复杂三档收敛后都直接进入对应下一跳。单独「继续」只对退出点造成的 `已停` 无效。排查写不出步骤、详细设计、以及危险操作、线上动作、泄密等退出点仍停。

执行中升到中等或复杂时停止改业务代码，改为 `已交接` 并按新档位衔接，不另问路由。已写下的「等走 task-explore」旧方案，在没有其他退出点时改为 `已交接` 并开工。

task-explore 自己的创建目录、选 explore 或 chat、确认冻结仍由该 skill 执行。wizard 不把这些门禁收成收敛后的选项，也不改 task-explore 的正文。

非目标：不改任务方案的确认；不改排查与详细设计的停；不改审阅的 P0/P1 核对；不把 skill 改成自进化。

## Conflict check

与现有「复杂档保持已停，直到用户说走 task-explore」冲突，本 patch 取代该条。与「不主动索取仍按此方案执行」一致，并补上不得在收敛后把它列成选项。与 task-explore 的目录创建、选阶段、冻结确认不冲突：那些门禁留在下游，wizard 不再预问。任务方案分支未改。

## Rationale

Goal 没有人盯着选路由。方案已经评审收敛时，再问走哪条衔接不增加信息，还会把「仍按此方案执行」误用成在本会话实施复杂档步骤。中等档收敛后已经直接进入 OpenSpec；复杂档对齐同一规则。用户已点名这条行为：收敛后不应再确认，goal 模式应减少确认。触发与授权门禁会改变 agent 行为，风险为 high；确认的是该契约。

## Files

- agents/skills/task-wizard/SKILL.md：Goal 减少确认；复杂档收敛后 `已交接` 并开始 task-explore；升档与旧方案不再等路由授权
- agents/skills/task-wizard/CONTEXT.md：授权只覆盖退出点已点名的动作，收敛后的档位路由不是待授权项

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 为 task-wizard；收敛后的复杂路由不再要求先说「走 task-explore」；排查停句仍在；无个人路径或密钥
