# 规格 / 对齐阅读页（spec-to-readable-html）

本文件是 pretty-view **第一方蒸馏**，不是第三方 skill，**禁止**做成 `SKILL.md`（避免被 Cursor 递归注册）。仅在门 3 已定为 HTML 阅读页、且命中本路径时 Read。

上游对照：`kemezz/spec-to-readable-html`（MIT）。本仓库不 vendor 其 `SKILL.md` / 千行模板；按下方规则**直写 `.html`**。落盘与索引仍走门卫 `SKILL.md`。

主题名：`spec-paper`。同项目同 refer 保持这套 token，不必每次确认。

**语言**：`<html lang="zh-CN">`。上游默认日语，**这里覆盖为简体中文**；标识符、路径、字段名、错误码保持原文。

## 何时用 / 何时不用

| 用 | 不用 |
|----|------|
| 规格、spec、RFC、PRD、需求、设计说明、问题对齐、可追溯、OpenAPI / API 合同 | 公众号 / 显式 md→html → baoyu |
| 要把密信息重组为：摘要、流程、要件表、风险、未决、溯源附录 | 路演 / 翻页 → `html-ppt` |
| | 以图解/对比/交互为主 → `html-artifact` |
| | 普通长文未点名规格 → `html-page` 或 `html-doc` |

这不是「把 Markdown 原样转成 HTML」。要分析、摘要、重组，并在不改原意的前提下加图。用户明确要求忠实转换时，才少重组、多保留原文结构。

## 工作流

1. 读源：标题、范围、实体、流程、API/数据、约束、风险、未决。
2. 按下方「章节序」重组；源里没有的章节**整节省略**，禁止空壳。
3. 要件 / API 合同 / 验收标准保持原文关键词（MUST / SHOULD / SHALL / 必选 / 可选）与 ID、路径、字段、枚举、错误码。
4. 背景与重复说明可摘要。推断标 `Inferred` / `Assumption`；猜不出就进「未决」，不要编。
5. 直写单文件 HTML（内联 CSS）。默认 `file://` 能开：图优先 inline SVG；仅当用户允许联网且图复杂时才用 Mermaid CDN，并在页脚注明。

## 章节序

1. Header：标题、副标题、元信息（类型 / 版本 / 日期 / 读者 / 源）
2. 侧栏 TOC（sticky；移动端改为文内目录）
3. 执行摘要（2–3 段 + 摘要卡）
4. 关键概念 / 术语
5. 主流程 / 用户旅程
6. 功能要件（表 + 优先级徽章）
7. 非功能要件
8. 系统 / API / 数据总览
9. 风险与未决
10. 附录：溯源表（输出节 → 源节；Preserved / Summarized / Inferred）
11. Footer：来源与生成日期

## 视觉选择

| 源内容 | 视觉 |
|--------|------|
| 步骤流程 | 流程图 |
| 系统间调用 | 序列图 |
| 组件与依赖 | 架构图 |
| 状态生命周期 | 状态图 |
| 实体关系 | ER / 关系图 |
| 里程碑 / 分阶段 | 时间线 |
| 方案取舍 | 对比矩阵 |
| 数量 / 优先级统计 | 柱状（**禁止编造数字**） |

每张图要有 `<figcaption>`，按「图 1、图 2」编号。

## 徽章

- 优先级：`Must` / `Should` / `Could`
- 状态：`Confirmed` / `Inferred` / `Assumption` / `Open Question`
- 风险：`High` / `Medium` / `Low`

## 布局合同（本路径）

- **文档栏 + TOC**，不是 `html-page` 的默认全宽，也不是 baoyu 的 680–800px 公众号栏。
- 主栏约 `min(820px, 100%)`，侧栏 TOC 约 `220px`；窄屏单列。
- 表格、代码、图与主栏同宽；长段落可读即可。
- 自包含：内联 CSS；不要引用 skill 目录。不要手写「← 目录」（catalog 会注入）。

## Token（`spec-paper`）

```css
:root {
  --bg: #fff; --surface: #f5f8f7; --line: #dfe7e5; --ink: #111;
  --muted: #626262; --accent: #2563eb; --accent-ink: #1d4ed8;
  --ok: #16a34a; --warn: #e8910c; --danger: #e03131;
  --font: ui-sans-serif, system-ui, "Noto Sans SC", sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
```

骨架：`<header class="doc-header">` + `<div class="doc-layout"><nav class="toc">` + `<article>`。语义标签：`section` / `table` / `figure`。源文本插入前转义 `& < > " '`。

## 不要

- 因为「要 HTML」就走 baoyu 或先写一份 `.md` 再转。
- 静默改合同语义；删规范性句子却不标「已摘要」。
- 把对齐文档做成翻页 PPT。
- `lang="ja"`（除非用户要日文）。
- 紫渐变 + Inter 灰卡片；空章节；无溯源的「精美改写」。
