# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-111615-review-role-based
- risk: medium
- status: applied
- applied-at: 2026-09-25T11:16+08:00

## Validation

- `git apply --check`: pass（`--recount` 对本 diff 误报，沿用历史 patches 的既有结论）
- `git diff --check`: pass
- target tests: not-available（skill 无自带测试；frontmatter 与 references 路径脚本核对通过）
- privacy check: pass
- mode check: pass（仅改 SKILL.md 三处，未触自进化目录与历史 patches/）

## Notes

medium 门禁：用户本轮明确要求「评审时引入 role-based-reviewer skill」并选定接入方式，视为已批准对应 diff。按 pwd-skill-manager 约定未自动 sync/commit，需 `dotf agents -c` 下发本机。

应用后核对：SKILL.md 三处均生效——人选分支新增一行、审阅者身份句补角色视角、退出点「审阅派不出」扩点名 skill 读不到。
