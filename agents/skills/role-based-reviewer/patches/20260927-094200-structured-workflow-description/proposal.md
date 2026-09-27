# description 承认结构化工作流调用

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260927-094200-structured-workflow-description
- risk: low
- status: proposed

## Intent

正文门 1 已承认「上游编排型工作流以 `mode=review` + 完整合法 `roles=` + 审阅边界输入调用」，但 frontmatter description 仍只写用户显式点名 / `roles=` / 明确岗位视角。宿主常用 description 做技能路由，可能在这种结构化调用时判定不触发。

本 patch 只把 description 补齐为：用户显式触发，或上游工作流结构化调用。正文行为不变。

## Conflict check

- 不放宽普通「帮我 review」的自动触发；description 仍明确普通 review 不自动加载。
- 与 ADR `0032-role-reviewer-accepts-structured-workflows.md` 一致。
- 不改门 1 / 门 2 / 门 3 和角色推断。

## Rationale

description 是宿主选择 skill 的第一入口；正文可用但 description 不承认，等于实际路由不可达。补一句可让 taskflow 的固定三角色审阅稳定到达现有实现。

## Files

- `agents/skills/role-based-reviewer/SKILL.md` — frontmatter description 增加结构化工作流调用

## Validation

- `git apply --check --recount`
- 应用后 `git diff --check`
- grep 确认 description 同时含「结构化」与「普通 review 不自动加载」
- frontmatter 可解析
