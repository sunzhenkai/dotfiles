# Result

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260925-030131-uiux-role
- risk: medium
- status: applied
- applied-at: 2026-09-25T03:01:31+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available（本 skill 无自带测试；以逐文件 cmp 比对替代：6 个文件与应用前 b 侧预期完全一致）
- privacy check: pass（无个人/凭据/内部 URL；来源为公开开源 skill 的通用实践改写）
- mode check: pass（update 模式，未引入 examples/evals/experience）

## Notes

- 6 个文件落盘：SKILL.md + 4 个 references 修改，新增 references/ui-ux-checklist.md（8 维 55 条，🔴12 / 🟡26 / ⚪17，[代码] 45 / [运行态] 10）。
- `uiux` 别名在 SKILL.md（description/合法值/推断信号）、role-vocabulary.md（角色矩阵行 + 组合规则）、brief-protocol.md（RoleBrief 枚举）、preload-protocol.md（design 锚点）四处表述一致；constraints.md 未出现别名属预期（命令边界表按列归属，无需别名）。
- 清单仅由 preload-protocol 在 design/uiux 生效时引导加载，SKILL.md 的 MUST 先读取四件套不变。
- 与 proposal 无偏差。
