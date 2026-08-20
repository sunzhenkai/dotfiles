# 切换 Chicago Day 并修正宽度约束

- target: agents/skills/pretty-view-html
- patch: 20260820-232700-chicago-day-layout-fix
- risk: high
- status: proposed

## Intent

将固定视觉系统从 Atelier Seaside Light 切换为 Chicago Day，并移除统一规定 `1600px` 容器和 `80–90ch` 正文宽度的行为，改为根据内容类型、阅读任务和视口自适应决定布局宽度。

非目标：不改变同主题归类流程、吸顶导航、文件组织或其他可访问性要求。

## Conflict check

固定主题色值会被整体替换。工作区中两条旧宽度规则已由用户先行删除，本 patch 不覆盖该修改，而是新增明确的自适应宽度规则，将用户确认的修复固化为可执行行为。与其他流程和引用无冲突。

## Rationale

Chicago Day 是仓库内已有、可核对的 Base16 主题。固定的像素与字符宽度会机械约束不同类型的阅读页；改为按内容和视口选择宽度，可避免窄化宽表格、图文页面或高密度内容，同时仍由现有响应式和可读性要求兜底。

## Files

- `agents/skills/pretty-view-html/SKILL.md`：替换固定色板，并明确禁止套用统一宽度上限。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check -- agents/skills/pretty-view-html`。
- 核对 Chicago Day 色值、宽度规则、frontmatter、引用路径和隐私信息。
