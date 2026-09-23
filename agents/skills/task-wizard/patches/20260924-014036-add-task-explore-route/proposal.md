# 重排复杂度路由：简单/中等先 grill-with-docs，复杂走 task-explore→taskflow

- target: agents/skills/task-wizard
- mode: update
- patch: 20260924-014036-add-task-explore-route
- risk: medium
- status: proposed

## Intent

现状：task-wizard 的复杂度路由是三档「简单（直接实现）/ 中等（OpenSpec）/ 复杂（taskflow）」，复杂度直接决定实现路径，没有「先把方案拷问清楚」的统一前置。

目标路由（用户指定）：

| 档 | 衔接 |
|----|------|
| 简单 | 产出步骤 → 走 grill-with-docs 拷问、梳理清楚 → 直接按步骤实现 |
| 中等 | 简单之外，再走 OpenSpec 流程实现（`openspec-propose` → `openspec-apply-change`） |
| 复杂 | 走 task-explore → taskflow |

改动：路由表按此重写；「中等」定义为「在简单之上，需 spec 契约或正式验收」，承接简单那套拷问前置；「复杂」直接进 task-explore，由探索梳理清楚后 `handoff` 给 taskflow，不再从 task-wizard 直接进 taskflow。补三条要点：先拷问后实现、grill-with-docs 两跳原文保留、方案正文原文带入下游。description 路由串同步改为 `grill-with-docs / OpenSpec / task-explore+taskflow / 直接实现`。

非目标：不动「原则 / 工作流 / 输出模板 / 边界」；不改变 task-wizard 的触发条件与产物形态；不新增执行步骤。

## Conflict check

- `grill-with-docs` 是两跳调用（`grilling` + `domain-modeling`，见其 SKILL.md 正文）。task-explore 的 `explore` 阶段**禁止**调用它（会写仓库根 `CONTEXT.md` / `docs/adr/`，与任务目录落点冲突）；本改动只在 task-wizard 的简单/中等档引用，复杂档走 task-explore 本身，不路由到 grill-with-docs，二者不冲突。
- 复杂档从「task-wizard → taskflow」改为「task-wizard → task-explore →（handoff）→ taskflow」，与 task-explore 的 `handoff` 出口（建同名 `{task}-driver`）一致；taskflow 仍是最终编排者，职责不变。
- task-wizard 无契约测试，无被钉住的文本受影响。
- `agents/skills.yaml` 已同时收录 grill-with-docs / task-explore / taskflow / task-wizard，无需改编目。

## Rationale

按 writing-for-agents：复杂度仍是一次分支判断，一行一档；简单/中等共享「先拷问问清」这一前置，只在「产不产 spec、走不走 OpenSpec」上分叉，故「中等」用「在简单之上」表达，避免把拷问步骤写两遍。grill-with-docs 的两跳调用是其契约原文，单列一条要点头避免被简写成一跳。

## Files

- agents/skills/task-wizard/SKILL.md — description 路由串改为 grill-with-docs / OpenSpec / task-explore+taskflow；路由表三档「衔接」重写；要点补「先拷问后实现」「grill-with-docs 逐字两跳」「下游原文带入」

## Validation

- 应用前：`git apply --check --recount`（已通过）
- 应用后：`git diff --check`；frontmatter `name` 与目录名一致；渲染路由表确认三档衔接与用户指定一致
