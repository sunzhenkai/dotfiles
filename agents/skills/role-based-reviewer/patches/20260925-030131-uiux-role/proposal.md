# design 角色升级为 UI/UX 评审并接受 uiux 别名

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260925-030131-uiux-role
- risk: medium
- status: proposed

## Intent

把 `design` 角色从一句话职责升级为带检查清单的完整 UI/UX 评审能力（交互流程、信息架构、可用性启发式、无障碍、视觉一致性、响应式、微文案、状态覆盖），并接受 `uiux` 作为 `design` 的等价别名（`roles=uiux` ≡ `roles=design`）。

非目标：不改变三道门禁、不新增独立角色、不改变其他角色职责；纯 diff 评审中运行态条目降级为「⚠ 需运行态验证」提示，不起服务、不截图。

## Conflict check

- 与现有 `design` 职责不冲突：原定义（视觉/交互一致性、布局间距、可用性、无障碍、响应式）已在 UI/UX 范围内。升级为带清单的评审能力，避免新增并列角色造成主问题域重叠、UI 评审被迫双开（门 2 防角色膨胀）。
- 与其他角色边界不变：需求范围与价值仍归 product，实现与性能仍归 engineer；redirect 表不动。
- 不引入自进化结构（examples/evals/experience），非 self-upgrade。

## Rationale

开源实践可复用且经分级后可直接对接门 3：vercel-labs/web-interface-guidelines 提供 100+ 条可静态判定规则（file:line 输出与本 skill findings 同构）；anthropics/frontend-design 提供微文案原则与 anti-slop 清单；Nielsen/WCAG 提供启发式与无障碍检查维度。约七成条目纯代码可判。

## Files

- `agents/skills/role-based-reviewer/SKILL.md`：description、合法值、推断信号三处加 `uiux` 别名
- `agents/skills/role-based-reviewer/references/role-vocabulary.md`：design 行职责扩充；组合规则声明 `uiux` 视为 `design`
- `agents/skills/role-based-reviewer/references/constraints.md`：命令边界表 design 列视角细化
- `agents/skills/role-based-reviewer/references/preload-protocol.md`：design 锚点指向新清单（仅角色生效时加载，不增加全局阅读负担）
- `agents/skills/role-based-reviewer/references/brief-protocol.md`：RoleBrief 角色枚举加别名
- `agents/skills/role-based-reviewer/references/ui-ux-checklist.md`：新增，8 维 55 条分级清单（🔴/🟡/⚪ × [代码]/[运行态]）

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；SKILL.md frontmatter `name` 与目录名一致；清单中引用的 `preload-protocol.md` 相对路径存在；diff 不含 `patches/` 历史、镜像路径或绝对路径；`uiux` 别名在 5 处文档表述一致
