# 切换 Chinoiserie 并增强表达组件与配色

- target: agents/skills/pretty-view-html
- patch: 20260821-001838-chinoiserie-expressive-components
- risk: high
- status: proposed

## Intent

将固定视觉系统从 Chicago Day 切换为 Chinoiserie，并要求生成时按内容职责主动使用表达力更强的组件（内容表达、标签/徽章、架构/可视化、对比/决策、教程/操作、数据/状态），同时在色板内更积极地用强调色突出重点、状态与结构。

非目标：不改变同主题归类、文件组织、本地链接规则、吸顶导航或自适应宽度；不引入运行时主题文件依赖；不修改历史输出或 agent 镜像目录。

## Conflict check

固定主题色值与“强调色尽量少用”的旧约束会被整体替换。新增组件表会提高视觉密度，但通过禁止虚构信息、禁止卡片海洋和无意义装饰，与现有“内容优先、可访问性、颜色不单独传达含义”规则兼容。与 `frontend-design` 通过保留主题驱动的字体、版式与克制视觉特征兼容。

## Rationale

Chinoiserie 是仓库内可核对的 Base16 light 主题，暖棕灰阶加朱砂/赭石/帝王黄等强调色，适合阅读页做重点编码。把组件职责与色义写成可执行表，可跨项目验证，避免继续生成“灰段落 + 标题”的弱表达页面。

## Files

- `agents/skills/pretty-view-html/SKILL.md`：替换色板、新增表达组件与用色指引，并更新完成检查。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check -- agents/skills/pretty-view-html`。
- 核对 Chinoiserie 色值、组件职责表、Chicago Day 残留、frontmatter、引用路径和隐私信息。
