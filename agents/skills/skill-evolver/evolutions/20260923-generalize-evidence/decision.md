# Decision — 20260923-generalize-evidence

decision: promote

原因：
- 用户已确认 proposal.yaml 与候选 diff
- eval.md 结论 pass（回归、模式、契约、副作用均通过）
- 候选 diff 与 proposal 一致，无夹带编辑

动作：候选 `SKILL.md` 覆盖生产稿 `agents/skills/skill-evolver/SKILL.md`。
未 sync、未 commit —— 由用户决定何时 `dotf agents -c` 下发到 `~/.agents/skills/` 镜像。
