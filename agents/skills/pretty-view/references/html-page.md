# 全宽 HTML 阅读页

本文件是 pretty-view **第一方**说明，不是第三方 skill，不会独立触发。仅在介质已定为 HTML、形式为阅读页、且不走 baoyu / html-ppt / html-slides 时 Read。

**直写一个可打开的 `.html`。** 不要写临时 Markdown，不要加载 baoyu。落盘与索引仍走门卫 `SKILL.md`。

## 布局合同

| 规则 | 要求 |
|------|------|
| 默认全宽 | `html, body { width:100%; margin:0 }`。主栏**不设** `max-width`。左右 padding 用 `clamp(24px, 4vw, 56px)` |
| 限宽（仅改口） | 用户说「不要太宽 / 限宽」→ 主栏 `max-width:1320px; margin:0 auto` |
| 窄栏（禁止当默认） | `max-width: 680–800px` 居中 = 公众号栏。只在用户要公众号/微信/阅读栏，或走 baoyu 时出现 |
| 块级同宽 | `table` / `pre` / `figure` / `.grid` 宽度 `100%`。不要在全宽壳里再套一层窄栏正文 |
| 段落可选 | 长文可读性不够时，只给 `p` / `.lede` 设 `max-width:72ch`，不要收整个 `.page` |
| 自包含 | `file://` 能开。内联 CSS 或同目录相对路径。不要引用 skill 目录。不要默认外链 JS 框架 |
| 回链 | 不要手写「← 目录」。catalog 脚本在 `<body>` 后注入 |

根 `index.html` 由 `scripts/update-catalog.py` 生成，禁止手改。

## 骨架

复制后填入正文。token 可按内容微调，不要改成紫渐变 / Inter 灰卡片。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>标题</title>
<style>
  :root {
    --ink: #1c1917;
    --muted: #78716c;
    --line: #e7e5e4;
    --bg: #fafaf9;
    --card: #ffffff;
    --accent: #1d4ed8;
  }
  * { box-sizing: border-box; }
  html, body { width: 100%; margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.6 ui-sans-serif, system-ui, "Noto Sans SC", sans-serif; }
  .page { width: 100%; padding: 40px clamp(24px, 4vw, 56px) 80px; }
  h1 { font-size: 2rem; font-weight: 650; letter-spacing: -.02em; margin: 0 0 8px; }
  .lede { color: var(--muted); margin: 0 0 32px; }
  h2 { font-size: 1.15rem; margin: 36px 0 12px; padding-top: 24px; border-top: 1px solid var(--line); }
  h3 { font-size: 1rem; margin: 20px 0 8px; }
  p { margin: 0 0 12px; }
  a { color: var(--accent); }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
  pre, .grid, figure { width: 100%; }
  pre { overflow: auto; background: #1c1917; color: #f5f5f4; padding: 16px 20px; font-size: 13px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
  .card { background: var(--card); border: 1px solid var(--line); padding: 16px 18px; }
  .callout { border-left: 3px solid var(--accent); padding: 8px 14px; background: #eff6ff; }
  @media (max-width: 640px) { h1 { font-size: 1.6rem; } }
</style>
</head>
<body>
<main class="page">
  <header>
    <h1>标题</h1>
    <p class="lede">结论或 TL;DR，3–7 行。</p>
  </header>
  <article>
    <!-- 按内容类型填：结论 → 背景 → 要点 → 细节 -->
  </article>
</main>
</body>
</html>
```

## 内容块

- 对比 / 清单 / 评审：`<table>`，全宽。
- 并行要点：`.grid` > `.card`。
- 决策 / 风险 / 待确认：`.callout`，不要埋进段落。
- 代码：`<pre><code>`，横向滚动，不要缩小成中间一列。
- 骨架复用门卫 SKILL.md「按内容类型」（文档 / 报告 / 方案 / review）。

## 不要

- 先写 `.md` 再转换（除非用户显式 md→html 或要公众号）。
- 给 `.page` / `main` 加 `max-width: 800px` 以下。
- 手写与 catalog 冲突的顶栏回链。
- 外链未说明的字体 / 图标 CDN（系统字体即可）。
