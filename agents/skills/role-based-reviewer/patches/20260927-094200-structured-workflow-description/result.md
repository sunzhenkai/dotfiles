# Result

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260927-094200-structured-workflow-description
- risk: low
- status: applied
- applied-at: 2026-09-27T09:43+08:00

## Validation

- `git apply --check --recount`: pass
- reverse rollback then apply: pass
- `git diff --check -- agents/skills/role-based-reviewer`: pass
- description 同时保留结构化工作流调用与普通 review 不自动加载
- frontmatter / 正文行为未其它改变

## Notes

仅修宿主路由入口描述；未 sync、未 commit。
