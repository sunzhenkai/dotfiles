# Result

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260925-031016-split-role-files
- risk: medium
- status: applied
- applied-at: 2026-09-25T03:10:16+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available（本 skill 无自带测试；以逐文件 cmp 比对替代：3 个修改文件 + 9 个角色文件与应用前 b 侧预期完全一致）
- privacy check: pass（无个人/凭据/内部 URL；清单条目为通用工程实践）
- mode check: pass（update 模式，未引入 examples/evals/experience）

## Notes

- 9 个角色文件落盘：`references/roles/{engineer,algo,data,sre,ops,biz,product,design,qa}.md`，各含优先锚点、核心检查清单（🔴/🟡/⚪ 分级，12–18 条/角色）、下游建议、跨角色 redirect。
- `roles/design.md` 整体并入上一轮 `ui-ux-checklist.md` 的 55 条内容（条目原文未改），`ui-ux-checklist.md` 已删除，全仓无残留引用。
- preload-protocol 各角色锚点表已下沉；role-vocabulary 保留角色矩阵与共享对象归属，组合规则新增角色文件分工声明；SKILL.md 流程第 2 步声明按角色加载且计入 ≤6 文件预算。
- 约束不变：三道门禁、严重级别、brief-protocol 骨架、constraints redirect 总表均未动。
- 注：上一轮（030131-uiux-role）的改动在本轮应用前已被 stage 未提交（git status 显示 A/MM），本轮在其工作区基础上叠加，两套改动现同在未提交区，由用户决定提交方式。
- 与 proposal 无偏差。
