# Result

- target: agents/skills/task-explore
- patch: 20260915-163832-split-heavy-phases
- risk: medium
- status: applied
- applied-at: 2026-09-15T16:39:22+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available
- privacy check: pass
- frontmatter `name` = directory `task-explore`: pass
- `SKILL.md` 不再内嵌设计对比表：pass
- `references/phase-explore.md`、`references/phase-design.md` 存在且被主文件引用：pass

## Notes

`SKILL.md` 231 → 175 行。`chat` / `resume` / `new` / `save` / `archive` 仍留在主文件（步骤短，默认路径常用）。
