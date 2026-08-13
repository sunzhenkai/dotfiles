# 通用技术文档阅读页（html-doc）

本文件是 pretty-view **第一方蒸馏**，不是第三方 skill，**禁止**做成 `SKILL.md`。仅在门 3 已定为 HTML 阅读页、且命中本路径时 Read。

上游对照：`jeffpoulton/html-doc`（skills.sh 公开摘要；GitHub 仓库拉取失败，**未 vendor 原文 `base.css`**）。下面的 token / 组件是本仓库按该摘要重写的设计系统：给人看的文档默认出 HTML；同一套组件，只改强调色。落盘与索引仍走门卫。

主题名：`ink-paper`。同项目同 refer 保持；换气质时只改 `--accent`（及成对的 `--accent-ink`），不要另起一套皮肤。不必每次确认。

## 何时用 / 何时不用

| 用 | 不用 |
|----|------|
| 「做好看的技术文档」、给人在浏览器里读/打印/转发的说明 | 规格/RFC/对齐/可追溯 → `spec-to-readable-html` |
| 需要稳定的文档组件（元信息条、呼出、表、代码、kbd），而不是一次一换的视觉实验 | 图解/对比/时间线/可交互思考面 → `html-artifact` |
| 读者是人，不是下一个 agent | 普通无结构长文 → `html-page` |
| | 给 agent / PR / README 的文本 → 内置 Markdown |
| | 公众号 / md→html → baoyu；翻页 → `html-ppt` |

**受众决定介质**：人读 → 本路径 HTML；agent 或渲染器要纯文本 → Markdown。不是按「内容是不是技术」来选。

## 工作流

1. 确认读者是人、形式是阅读页（不是 PPT、不是公众号）。
2. 复制下方 token + 组件 CSS，只选定一个强调色（默认蓝墨）。
3. 直写单文件 HTML：内联 CSS，含 `prefers-color-scheme` 暗色。不要外链框架。
4. 用组件，不要每段一个卡片。表给表、呼出给决策/风险、代码给代码。
5. 一个 H1；开头结论或 TL;DR；语义标签。

## Token（`ink-paper`）

```css
:root {
  --bg: #f7f4ef; --card: #fffaf3; --ink: #1c1917; --muted: #78716c;
  --line: #e7e0d6; --accent: #1d4ed8; --accent-ink: #1e3a8a;
  --ok: #166534; --warn: #b45309; --danger: #b91c1c;
  --font: ui-sans-serif, system-ui, "Noto Sans SC", sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --measure: 72ch;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1917; --card: #292524; --ink: #f5f5f4; --muted: #a8a29e;
    --line: #44403c; --accent: #93c5fd; --accent-ink: #bfdbfe;
  }
}
```

换强调色时成对改 `--accent` / `--accent-ink`（例如石青、赭石），其余 token 不动。

## 布局合同（本路径）

- 页面铺满视口；**正文** `max-width: var(--measure)`，表 / 代码 / 图可撑到主栏（主栏 padding `clamp(24px, 4vw, 56px)`，主栏本身可不设死宽）。
- 不是 `html-page` 那种整页强制全宽无栏，也不是 baoyu 窄栏。
- `file://` 能开。不要手写「← 目录」。可加打印样式（`@media print` 去背景、显链接）。

## 组件

| 块 | 用法 |
|----|------|
| `.meta` | 类型 / 日期 / 读者，一行小字 |
| `.lede` | 结论，3–7 行 |
| `.callout` | 决策、风险、待确认；变体 `--warn` / `--danger` |
| `table` | 对比、清单、接口字段 |
| `pre code` | 代码；横向滚动 |
| `kbd` | 快捷键 |
| `.grid` | 仅当两项以上真正并列时 |

骨架：`header`（H1 + `.meta` + `.lede`）→ `article` 按文档/报告/方案骨架填。不要居中 hero、不要顶栏营销导航。

## 不要

- 先写 `.md` 再转换；把「技术文档」做成 PPT 或公众号。
- 每篇换一套渐变皮肤；紫渐变 + Inter 灰卡片。
- 假暗色（只反色而不改对比）。
- 为「好看」丢掉接口路径、约束、未决。
