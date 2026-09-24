# Goal 方案：处在 goal 里时写给 agent 并执行到完成判据或退出点

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-021056-goal-plan
- risk: high
- status: proposed

## Intent

在已有任务方案之外，增加 Goal 方案分支。触发：消息里看得到 `/goal`，或当前有进行中的 goal 且本条消息挂了本 skill。没有进行中的 goal 时，任务方案的确认、路由与边界保持原样。

Goal 方案只写在当轮回复里。简单档同一轮接着做到完成判据或退出点，不插入 grill-with-docs。中等 / 复杂只出方案，路由句自洽，等用户明确授权那条路由后再衔接。退出点、授权、「继续」不算授权、升档即停、做完才标完成，都写进该节。

非目标：不把 skill 改成自进化；不改 task-explore / OpenSpec / taskflow 自身；不落方案文件；不自动 sync、commit 或 push。

## Conflict check

- 「先拷问后实现」与 Goal 简单档冲突。处理：该条标明只约束任务方案；Goal 简单档不插入 grill。
- 任务方案边界「直接改代码则退出」与 Goal 简单档冲突。处理：该边界节标题收成任务方案；Goal 节允许方案之后改代码。排查与详细设计在 Goal 路径仍不套模板。
- 中等 / 复杂的路由句沿用现有衔接：grill 两跳不简写，task-explore 不下新任务名、不重演探索，正文原样带入。
- 公开 skill 不在新段落写入仓库专属安装命令。Goal 节只写「给出安装选项」；任务方案里已有的示例命令保持不动。

## Rationale

goal 会跨回合做到完，而本 skill 只在当轮挂上。方案正文和退出条件必须自洽，否则淡出后守不住。用户已逐条确认该行为。

## Files

- agents/skills/task-wizard/SKILL.md — 分流、收紧任务方案边界的适用范围、新增 Goal 方案节、更新 description 触发
- agents/skills/task-wizard/CONTEXT.md — Goal 方案相关术语

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；任务方案模板与三档路由表仍在；Goal 节含完成判据、七个退出点短标签、中等 / 复杂固定路由句
