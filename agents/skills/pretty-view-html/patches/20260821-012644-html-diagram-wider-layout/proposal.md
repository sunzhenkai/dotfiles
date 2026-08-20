# 接入 html-diagram 并放宽桌面阅读宽度

- target: agents/skills/pretty-view-html
- patch: 20260821-012644-html-diagram-wider-layout
- risk: medium
- status: proposed

## Intent

1. 当页面内容需要 diagram（架构/流程/关系/状态/时序等）时，先读取本地 reference `references/html-diagram/SKILL.md`（vendored 自 plannotator/effective-html 的 html-diagram），按其模型选择与绘制原则生成，并默认嵌入当前阅读页。
2. 桌面端阅读布局默认偏宽：内容容器常见上限约 `1200–1600px`，长文可略收窄，表格/图解等用满容器；仍保持按内容自适应，避免机械单一固定宽度。

非目标：不改变同主题归类、文件组织、本地链接、Chinoiserie 色板或吸顶导航；不修改 agent 镜像目录；不引入必须联网的外部 diagram 服务。

## Conflict check

- 上游 html-diagram 默认“交付独立自包含 HTML”，与本 Skill 的阅读页交付冲突；已在 reference 与工作流中明确：经 pretty-view-html 调用时嵌入阅读页，除非用户要求独立产物。
- 上游提到的 `design-artifact` 未随本仓库 vendoring；改为服从本 Skill 的 Chinoiserie + frontend-design。
- 宽度规则与既有“禁止统一固定 max-width”兼容：改为偏宽偏好 + 自适应，而不是恢复机械单一像素上限。

## Rationale

把 diagram 专业指引固化为本地 reference，可离线复用且与 frontend-design 引用方式一致。偏宽布局回应“页面内容宽度酌情宽一些”，同时保留窄屏与长文可读性兜底。

## Files

- `agents/skills/pretty-view-html/references/html-diagram/SKILL.md`：新增 vendored diagram reference（含 embedding/palette 适配说明）。
- `agents/skills/pretty-view-html/SKILL.md`：工作流、表达组件、布局与完成检查接入该 reference，并放宽桌面宽度偏好。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check -- agents/skills/pretty-view-html`。
- 核对 reference 路径存在、frontmatter、上游来源说明、隐私信息与镜像目录未改动。
