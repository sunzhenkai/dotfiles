# Result

- target: agents/skills/project-init
- mode: update
- patch: 20260924-012843-nextjs-support
- risk: medium
- status: applied
- applied-at: 2026-09-24T01:31:12+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-init/tests` — 10 passed
- privacy check: pass（仅 `__pycache__` 内嵌绝对路径，已被 .gitignore 忽略且非本 patch 内容）
- mode check: pass

## Notes

- SKILL.md frontmatter `name`/`id` 仍为 `project-init`，与目录名一致；引用路径 `references/*.md` 均存在。
- 保持 frontmatter description 不含框架名（渐进披露），新增测试 `test_nextjs_not_in_frontmatter` 锁定该口径。
- 未自动 sync / commit / push；如需下发本机可跑 `dotf agents -c` 或对应 sync。
