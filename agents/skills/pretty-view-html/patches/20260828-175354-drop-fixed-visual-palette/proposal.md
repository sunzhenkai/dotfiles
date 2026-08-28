# 取消固定色板与硬编码视觉限制

- target: agents/skills/pretty-view-html
- patch: 20260828-175354-drop-fixed-visual-palette
- risk: medium
- status: proposed

## Intent

取消「所有页面必须使用 Chinoiserie（或任何单一固定色板）」的行为：生成前按 frontend-design 为本次主题选定配色、字体、版式和一个克制视觉特征，色值仍直接写入 HTML。表达组件表的用色提示改为语义角色（错误/警告/成功/信息/强调），不再点名固定色值。吸顶导航、表达组件类型、可读性/对比度、文件组织与链接规则保持不变。

非目标：不改同主题归类、本地链接、多页结构、html-diagram 选型与嵌入方式；不改写历史输出 HTML；不引入运行时主题文件或必须联网的样式依赖。

## Conflict check

本改动撤销先前 Chinoiserie 固定色板对 frontend-design「按主题选色」的覆盖，使父 Skill 与 reference 一致。html-diagram 中两处「服从 Chinoiserie」改为服从本次选定的页面视觉语言。保留「颜色不单独传达含义」与对比度要求，不与无障碍规则冲突。不触及其他 Skill 职责。

## Rationale

阅读页的视觉应服务具体主题，而不是全站锁死一套色值。去掉固定色板后，跨项目仍可执行：同包共用视觉语言、状态用语义色编码、色值内联、导航与组件约束不变。可通过静态检查确认 Skill 正文不再要求特定 hex 或 Chinoiserie 色名。

## Files

- `agents/skills/pretty-view-html/SKILL.md`：工作流、视觉语言、表达组件用色提示、布局与完成检查去掉固定色板。
- `agents/skills/pretty-view-html/references/html-diagram/SKILL.md`：父 Skill 配色约束改为页面选定视觉语言。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check -- agents/skills/pretty-view-html`。
- 核对正文与 html-diagram 不再出现 Chinoiserie 或锁定 hex；frontmatter、引用路径、吸顶导航与表达组件职责表仍在；无隐私信息。
