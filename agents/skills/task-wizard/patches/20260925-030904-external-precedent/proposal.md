# 复杂档定稿前做一次外部参照

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-030904-external-precedent
- risk: high
- status: proposed

## Intent

任务方案和 Goal 方案只在复杂档、定稿前做一次外部参照，避免闭门造车。本仓摸底之后，档位是复杂，或写到定稿前升到复杂，才检索公开资料并阅读最多两处公开原文。只追最会影响步骤的那一个做法。对上原文的写入前提的事实，对不上的写入假设。两处做法相反时两条都是事实，步骤采纳一条，另一条写入坑；选定不了就是决策点。简单和中等不检索仓外资料。建议路由在这次之后按事实重判。Goal 在审阅前写入前提；会改步骤或完成判据的假设仍走「理解不够」。

非目标：不改 task-explore；不新设退出点；不新开方案小节；不点名 MCP；不把 skill 改成自进化；不自动 sync、commit 或 push。

## Conflict check

- 「先查后问」仍只覆盖本仓代码、文档、环境。外部参照是复杂档单独一步，简单和中等不进入。
- Goal 的「理解不够」保留：外部参照留下的、会改步骤或完成判据的假设，仍走该退出点。缺检索结果本身不新设退出点。
- 半屏模板不新增小节。事实和假设仍在前提。
- 审阅仍在外部参照之后，审阅者看到的是已经写入前提的结果。
- 公开 skill 的新段落不写 MCP 服务器名、内部 URL、公司仓库。

## Rationale

复杂档若只看本仓就定步骤，会把没对照过公开做法的方案交出去。用户已逐条确认：只在复杂档查、失败记假设并照常写完方案、矛盾的两条都留作事实。触发和对外读取会改变 agent 行为，风险为 high；确认的是该契约。

## Files

- agents/skills/task-wizard/SKILL.md — 任务方案增加外部参照步骤；Goal 在审阅前指向同一规则；复杂档正文带上事实与假设
- agents/skills/task-wizard/CONTEXT.md — 外部参照、闭门造车
- agents/skills/task-wizard/references/external-precedent.md — 一次尝试的做法、出处和写入规则

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；简单/中等路由仍不检索仓外；复杂档指向 `references/external-precedent.md`；Goal 仍先审阅再按置信度继续；无外部参照测试（本 skill 无测试）
