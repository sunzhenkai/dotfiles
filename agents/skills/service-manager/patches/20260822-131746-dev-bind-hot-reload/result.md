# Result

- target: agents/skills/service-manager
- patch: 20260822-131746-dev-bind-hot-reload
- risk: medium
- status: applied
- applied-at: 2026-08-22T13:18:53+08:00

## Validation

- `git apply --check --recount`: pass（应用前已校验；应用成功）
- `git diff --check`: pass
- target tests: evals 用例 id `start-dev-prefer-hot-reload`、`start-dev-bind-all-interfaces` 已写入；无独立可执行测试套件
- privacy check: pass（无绝对家目录/凭据；frontmatter `name` == `service-manager`）

## Notes

- 用户确认后应用；实际 diff 与 proposal / `change.patch` 一致（SKILL.md + evals/cases.yaml）。
- 未执行 sync / commit / push。
