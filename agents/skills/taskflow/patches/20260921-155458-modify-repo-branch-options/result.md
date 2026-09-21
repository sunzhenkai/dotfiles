# Result

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-155458-modify-repo-branch-options
- risk: medium
- status: applied
- applied-at: 2026-09-21T15:55+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `yaml.safe_load(evals/cases.yaml)` pass（15 cases）
- privacy check: pass
- mode check: pass

## Notes

实际 diff 与 proposal 一致：SKILL.md 三处（Driver 协议切分支条目、propose 骨架 1.1、纪律「涉及面与交付分支」）+ cases.yaml 的 `fail-closed-must-repos`。Driver 协议模板与纪律段措辞语义一致。带脏切换从禁区转为用户显式选项；fail closed 保留禁止 stash / reset / 强制切换。
