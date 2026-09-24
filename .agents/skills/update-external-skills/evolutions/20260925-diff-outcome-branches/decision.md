# Decision — 20260925-diff-outcome-branches

**promote**（2026-09-25）

- 用户确认提案与候选 diff；eval 四项（回归 / 模式 / 契约 / 副作用）pass。
- 候选 SKILL.md 已覆盖生产稿 `.agents/skills/update-external-skills/SKILL.md`，
  改动仅限 step 4 差异判读段（+9/-1），与 proposal 一致，无夹带。
- 同时关闭 2026-09-21 `optional-skills-verify` 提案的未落地缺口：本轮把「diff -r 报
  不存在 → 只信 tree_hash」从坑 9 的事实陈述升级为 step 4 的操作分支。
- 生产稿是项目级 skill（`.agents/skills/`），本会话内即时生效；其他 agent 运行时镜像
  需要时由用户自行 `dotf agents -c` 下发，本次未擅自同步、未提交。
