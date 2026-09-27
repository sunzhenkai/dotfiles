# Result

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260927-005051-workflow-caller
- risk: high
- status: applied
- applied-at: 2026-09-27T01:10+08:00

## Validation

- 初稿 `git apply --check`: fail（hunk 与当前源不匹配，未应用生产文件）
- orchestrator 用源文件副本重生成 unified diff：pass
- `git apply --check --recount`: pass
- applied: pass
- `git diff --check -- agents/skills/role-based-reviewer`: pass
- privacy scan（proposal + patch）: pass
- mode check: pass；只改 SKILL.md 门 1/门 2/输入/示例/视角推断，未触 references 与历史 patches/

## Notes
