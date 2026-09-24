# 再审只核对，派审贴上完成判据

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-062351-review-recheck
- risk: high
- status: proposed

## Intent

Goal 审阅改为：出方案时完成判据保持一条可检查的话，「不做的事」列出排除行为；派审提示词原样贴上这两处。再审只核对上一轮 P0/P1。同一条核过仍在，或第二次核对仍有 P0/P1，则审阅不通过。P2 只写入坑，不挡开工。边界外的新行为不写入。前提事实写错、因而走不到这条判据，仍是 P0 或 P1。

非目标：不新增术语；不审架构、接口或代码骨架；中或低且还有没核过的 P0/P1 时不退出；完善期间不改代码；不设轮次上限后开工。

## Conflict check

与 0028「还有下一条改法就继续」冲突：句子意见、已核过的同一条 P0/P1、以及完成判据与「不做的事」都没有的新行为，不再继续写。0027 的「中或低不因此退出」和 0029 的「不审设计」保留。任务方案分支不改。

## Rationale

用户已点名 apply `goal-review-recheck`，工件里写明了上述行为。高风险门禁视为已通过。核对预算只写在审阅节，纪律用一句话指向该节。

## Files

- agents/skills/task-wizard/SKILL.md — 派审提示词、核对预算、P0/P1/P2、退出点「审阅不通过」的指针
- agents/skills/task-wizard/CONTEXT.md — P0、P1、P2、完善、评审收敛、诚实结论、审阅范围

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；走读「P1×2 / P2×4 且第一次核对两条 P1 已消失 → 收敛」；派审贴上完成判据与「不做的事」，只写「范围同前」作废；边界外新行为不写入
