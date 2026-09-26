# 审阅人选引入 role-based-reviewer

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-111615-review-role-based
- risk: medium
- status: applied

## Intent

Goal 方案「审阅」节的人选新增一条分支：goal 原文或当轮用户消息点名 `role-based-reviewer`、写 `roles=`、或明确要求按岗位 / 多角色视角审时，委托 `role-based-reviewer`（`mode=ask`）做审阅，其分级发现映射为 P0/P1/P2（Blocker→P0、Major→P1、Minor/Suggestion→P2），完成程度仍按本节规则由执行者写入。触发场景：用户在 goal 里点名角色化评审。非目标：不改默认审阅人选（仍是宿主子 agent），不让 role-based-reviewer 成为默认审阅器（尊重其自身门 1），不改 P0/P1/P2 定义与核对流程。

## Conflict check

- 与 role-based-reviewer 门 1 一致：仅点名 / roles= / 明确多角色视角时进入，task-wizard 不自动加载它。
- 与 agent-roster 分支同构（点名才走）；同时点名时以当轮消息为准，仍冲突则取 role-based-reviewer（视角更具体）。
- 退出点「审阅派不出」定义扩一句：点名的审阅 skill 读不到。模板里退出点只列标签，不受影响。none 其余。

## Rationale

名册审阅（agent-roster）与默认子 agent 之间缺「命名视角」这一档：复杂方案的审阅常需要岗位视角（如 sre 看部署面、algo 看策略面），role-based-reviewer 正是现成编排，且其发现克制（门 3）与审阅范围纪律同向。映射规则让分级发现进入既有 P0/P1/P2 核对循环，可验证：派审提示词与返回映射均写在节内。

## Files

- agents/skills/task-wizard/SKILL.md — 人选新增 role-based-reviewer 分支；「审阅者是…」句补角色视角；退出点「审阅派不出」补点名 skill 读不到

## Validation

- `git apply --check --recount`
- `git diff --check -- agents/skills/task-wizard`
- 核对实际 diff 与 proposal 一致；frontmatter 合法；无隐私泄露；未触历史 patches/
