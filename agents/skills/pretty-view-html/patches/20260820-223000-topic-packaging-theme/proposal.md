# 同主题内容包与统一视觉系统

- target: agents/skills/pretty-view-html
- patch: 20260820-223000-topic-packaging-theme
- risk: high
- status: proposed

## Intent

当已有输出中存在与本次内容主题相同、适合共同维护的页面时，先提出内容包归类方案，经用户明确确认后再写入或重组 HTML；普通生成以及未发现可靠同主题内容时不增加额外确认门禁。统一采用 Atelier Seaside Light 配色、滚动吸顶顶部导航和更宽的内容容器，同时保留主题驱动的字体、版式与内容特征。

非目标：不按关键词机械合并弱相关内容，不静默迁移现有页面，不自动覆盖文件，不要求运行时读取仓库外部主题文件，也不修改历史输出。

## Conflict check

现有规则要求色彩由主题决定，并默认按单页或多页独立生成；固定配色和自动重组内容包会改变这两项行为。此次将明确以固定色板覆盖动态选色，并为同主题重组增加归类依据、用户确认、链接迁移和根索引更新门禁。与 `frontend-design` 的主题化要求通过保留主题驱动的字体、版式和视觉特征来兼容。

## Rationale

相同主题归入内容包可改善持续维护和导航，但归类具有语义判断且可能改变路径，因此必须由用户确认。固定色板与导航可建立稳定的站点识别；将明确色值和布局约束写入 Skill，可跨项目执行并通过静态检查验证。

## Files

- `agents/skills/pretty-view-html/SKILL.md`：增加同主题内容包确认流程、统一色板、吸顶导航、宽内容布局及对应完成检查。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check -- agents/skills/pretty-view-html`。
- 检查 frontmatter、相对引用、色值、确认门禁、导航与布局规则是否完整且无隐私信息。
