# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-111019-goal-keep-explore
- risk: medium
- status: applied
- applied-at: 2026-09-25T11:10+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available（skill 无自带测试；frontmatter 与 references 路径脚本核对通过）
- privacy check: pass
- mode check: pass（仅改 SKILL.md 两处行为文案，未触自进化目录与历史 patches/）

## Notes

medium 门禁：用户在本轮明确提出「goal 模式下不应跳过 explore 阶段」这一具体行为改动，视为已批准对应 diff。按 pwd-skill-manager 约定未自动 sync/commit，需 `dotf agents -c` 下发本机。
