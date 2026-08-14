# 统一 HTML 阅读页（html-page）

本文件是 pretty-view 的第一方统一阅读页 reference，不是第三方 skill，**禁止**改成 `SKILL.md`。介质已定为 HTML 且未命中 PPT、reveal.js 或显式 md→html 时，只 Read 本文件。

**直写一个可打开的 `.html`。** 不写临时 Markdown，不加载 baoyu / html-ppt / html-slides，也不搜索其他阅读页 reference。落盘与索引仍走门卫 `SKILL.md`。

- reference：`html-page`
- 主题：`stone-ink`
- 目标：规格、图解、技术文档、报告、方案、知识和长文看起来属于同一个产品，而不是多套孤立模板

## 核心合同：同壳、同 token、按内容换组件

所有阅读页必须复用以下四层：

1. **页面壳**：相同背景、顶部标识、主容器宽度、留白和响应式断点。
2. **排版**：相同字体栈、标题比例、正文行高、代码字体和链接样式。
3. **语义 token**：相同 `ink / muted / line / paper / accent / success / warning / danger`。
4. **组件**：摘要、元信息、callout、表格、代码、卡片、图示、时间线都来自同一组件族。

内容是规格、图解或技术文档，只改变结构和启用哪些组件；**不得**另起主题、换字体、换页面壳或引入另一套配色。用户要求换气质时允许整体调整 token，但同一产物和同一项目仍只保留一套 token。

## 内容模式

先判断内容模式，再在统一组件中取用。一个页面可组合相邻模式，但视觉系统不变。

| 模式 | 推荐结构 | 重点组件 |
|------|----------|----------|
| `spec` 规格 / RFC / PRD / 对齐 | 标题与状态 → 摘要 → 背景/目标 → 需求与约束 → 决策 → 可追溯 → 未决项 | `.meta`、`.status`、`.callout`、`.traceability` |
| `visual` 图解 / 架构 / 对比 / 时间线 | 标题 → 摘要 → 图例 → 主图/矩阵/时间线 → 证据与解释 | `.legend`、`.diagram`、`.comparison`、`.timeline` |
| `doc` 技术文档 / 操作说明 | 标题与元信息 → 摘要 → 分节正文 → 示例/代码 → 风险或注意事项 | `.toc`、`.callout`、`table`、`pre`、`kbd` |
| `article` 报告 / 方案 / 知识 / 长文 | 结论 → 背景 → 要点 → 细节 → 风险/下一步/参考 | `.lede`、`.grid`、`.metric`、`.references` |
| `review` HTML code review | 范围与结论 → 严重度分组 → 位置与证据 → 测试与残留风险 | `.finding`、`.severity-*`、`code`、`.callout` |

可在 `<body data-page-kind="spec|visual|doc|article|review">` 标记模式，便于维护；不要据此换主题。

## 单页 / 多页自动推断

默认生成**一个 HTML 页面**。长内容优先使用页内目录、锚点和分节；长度、章节数、表格、代码、图解或内容模式混合本身都不触发拆页。判断不确定时保持单页，不向用户追问。

仅在命中以下强信号时自动拆成多文件包：

- 用户明确要求多页、每章一页或文档站。
- 输入是多个独立文档，但需要统一入口。
- 存在总览和至少两个可独立查阅、独立分享或独立维护的模块。
- 不同部分面向明显不同的受众或维护周期。

自动拆页时先用一句话告知推断结果和页面地图，然后直接生成；拆页本身不需要确认。默认落盘根不存在、路径冲突等情况仍服从门卫 `SKILL.md` 的确认规则。

多页包合同：

```text
<kind>/YYYY-MM-DD-<slug>/
├── index.html          # 总览、结论、页面地图；唯一根入口
├── <topic-a>.html      # 独立模块，返回 index.html
├── <topic-b>.html      # 独立模块，返回 index.html
└── assets/             # 可选的包内资源
```

- 只允许一层附属页，不再嵌套子目录页面。
- `index.html` 必须链接全部附属页；每个附属页必须使用相对链接返回 `index.html`，并提供一致的包内导航。
- 所有本地 `href` / `src` 都使用相对路径；禁止绝对磁盘路径和 `file:///...`。
- 根 catalog 只登记 `index.html`。附属页不得单独登记，也不得成为无法从主文件访问的孤儿页。
- 每一页都复制同一套 stone-ink token、页面壳和组件；拆页只改变信息边界，不改变视觉系统。

## 布局合同

- `html, body { width: 100%; margin: 0; }`，背景铺满视口。
- `.shell` 是统一页面容器：`max-width: 1440px; margin: 0 auto; padding: 40px clamp(20px, 4vw, 56px) 88px`。
- 普通正文放在 `.prose`，建议 `max-width: 76ch`；它不是独立白卡，也不居中成公众号窄栏。
- 宽表、代码、图、矩阵和网格使用 `.wide`，可占满 `.shell`。不要为了正文行宽把信息密集块压窄。
- 有目录时使用 `.layout` 两栏：左侧 `.toc`，右侧正文；小屏退化为单栏。没有目录时仍复用同一 `.shell`。
- 统一 header 只放 eyebrow、H1、元信息和摘要；不要做营销导航、居中 hero 或大面积装饰封面。
- 根 catalog 注入的「← 目录」位于 `<body>` 后；正文不要手写同类回链。

## stone-ink token

除非用户明确要求整体换气质，否则复制这组 token，不要逐页随意改色。

```css
:root {
  color-scheme: light;
  --canvas: #f5f2ec;
  --paper: #fffdf8;
  --paper-strong: #ffffff;
  --ink: #1c1917;
  --muted: #78716c;
  --faint: #a8a29e;
  --line: #ded8ce;
  --line-strong: #c8bfb2;
  --accent: #1d4ed8;
  --accent-soft: #eaf1ff;
  --success: #166534;
  --success-soft: #ecfdf3;
  --warning: #a16207;
  --warning-soft: #fff8e1;
  --danger: #b91c1c;
  --danger-soft: #fff1f1;
  --code-bg: #211f1c;
  --code-ink: #f5f5f4;
  --shadow: 0 18px 50px rgba(54, 45, 35, .08);
  --sans: ui-sans-serif, system-ui, "Noto Sans SC", "PingFang SC", sans-serif;
  --mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --canvas: #171513;
    --paper: #211f1c;
    --paper-strong: #292623;
    --ink: #f5f2ec;
    --muted: #b8b0a5;
    --faint: #8f877e;
    --line: #3d3833;
    --line-strong: #544d46;
    --accent: #93b4ff;
    --accent-soft: #202c49;
    --success: #86d39a;
    --success-soft: #193222;
    --warning: #f1c56b;
    --warning-soft: #382d16;
    --danger: #f4a3a3;
    --danger-soft: #3d2020;
    --code-bg: #11100f;
    --code-ink: #f5f5f4;
    --shadow: none;
  }
}
```

## 基础骨架

按内容模式填充结构；可以删掉不用的组件，但不要替换页面壳和 token。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>标题</title>
<style>
  /* 复制 stone-ink token 到这里 */
  * { box-sizing: border-box; }
  html, body { width: 100%; margin: 0; }
  body { background: var(--canvas); color: var(--ink); font: 16px/1.7 var(--sans); }
  a { color: var(--accent); text-underline-offset: .18em; }
  .shell { width: 100%; max-width: 1440px; margin: 0 auto;
    padding: 40px clamp(20px, 4vw, 56px) 88px; }
  .page-header { padding: clamp(24px, 4vw, 52px); background: var(--paper);
    border: 1px solid var(--line); box-shadow: var(--shadow); }
  .eyebrow, .meta { color: var(--muted); font-size: .82rem; letter-spacing: .08em; }
  .eyebrow { text-transform: uppercase; font-weight: 700; }
  h1 { max-width: 24ch; margin: .35rem 0 .75rem; font-size: clamp(2rem, 5vw, 4.5rem);
    line-height: 1.04; letter-spacing: -.045em; }
  .lede { max-width: 76ch; margin: 0; color: var(--muted); font-size: 1.08rem; }
  .layout { display: grid; grid-template-columns: minmax(180px, 240px) minmax(0, 1fr);
    gap: clamp(28px, 5vw, 72px); margin-top: 36px; align-items: start; }
  .layout.no-toc { grid-template-columns: minmax(0, 1fr); }
  .toc { position: sticky; top: 20px; padding: 18px 0; border-top: 1px solid var(--line); }
  .toc a { display: block; padding: 5px 0; color: var(--muted); text-decoration: none; }
  .toc a:hover { color: var(--accent); }
  article { min-width: 0; }
  .prose { max-width: 76ch; }
  section { padding: 8px 0 28px; }
  h2 { margin: 36px 0 14px; padding-top: 22px; border-top: 1px solid var(--line);
    font-size: clamp(1.25rem, 2vw, 1.65rem); letter-spacing: -.02em; }
  h3 { margin: 24px 0 8px; font-size: 1.05rem; }
  p, ul, ol { margin: 0 0 14px; }
  .wide { width: 100%; max-width: none; margin: 24px 0; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
  .card { min-width: 0; padding: 18px; background: var(--paper);
    border: 1px solid var(--line); border-radius: 2px; }
  .callout { max-width: 76ch; margin: 18px 0; padding: 14px 16px;
    border-left: 3px solid var(--accent); background: var(--accent-soft); }
  .callout.success { border-color: var(--success); background: var(--success-soft); }
  .callout.warning { border-color: var(--warning); background: var(--warning-soft); }
  .callout.danger { border-color: var(--danger); background: var(--danger-soft); }
  table { width: 100%; border-collapse: collapse; font-size: .92rem; }
  th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
  th { color: var(--muted); font-size: .78rem; letter-spacing: .05em; text-transform: uppercase; }
  pre { width: 100%; overflow: auto; padding: 18px 20px; background: var(--code-bg);
    color: var(--code-ink); border-radius: 2px; font: .86rem/1.6 var(--mono); }
  code, kbd { font-family: var(--mono); }
  :not(pre) > code, kbd { padding: .12em .35em; border: 1px solid var(--line);
    background: var(--paper); font-size: .88em; }
  .diagram { min-height: 160px; padding: 20px; background: var(--paper);
    border: 1px solid var(--line-strong); overflow: auto; }
  .timeline { border-left: 2px solid var(--line-strong); padding-left: 22px; }
  .timeline > * { position: relative; margin-bottom: 20px; }
  .timeline > *::before { content: ""; position: absolute; left: -28px; top: .5em;
    width: 10px; height: 10px; border-radius: 50%; background: var(--accent); }
  .status { display: inline-flex; align-items: center; padding: 3px 8px;
    border: 1px solid var(--line-strong); color: var(--muted); font-size: .78rem; }
  @media (max-width: 820px) {
    .shell { padding-top: 20px; }
    .page-header { padding: 24px 20px; }
    .layout { grid-template-columns: 1fr; }
    .toc { position: static; }
  }
  @media print {
    body { background: #fff; color: #000; }
    .shell { max-width: none; padding: 0; }
    .page-header { box-shadow: none; }
    .toc { display: none; }
    a { color: inherit; }
  }
</style>
</head>
<body data-page-kind="article">
<main class="shell">
  <header class="page-header">
    <div class="eyebrow">内容类型 · 日期</div>
    <h1>标题</h1>
    <p class="meta">状态 / 受众 / 作者等必要元信息</p>
    <p class="lede">结论或 TL;DR，3–7 行。</p>
  </header>
  <div class="layout no-toc">
    <article>
      <div class="prose">
        <!-- 按内容模式组织正文 -->
      </div>
      <!-- 宽表、图、代码、矩阵放到 .wide -->
    </article>
  </div>
</main>
</body>
</html>
```

## 组件使用规则

- **摘要**：`.lede` 只放结论，不重复标题。
- **卡片**：只用于真正并列的对象；正文段落不要逐段卡片化。
- **callout**：默认用于信息/决策，`success` 用于已完成，`warning` 用于风险，`danger` 用于阻断项。
- **表格**：字段、对比、追溯、评审发现优先用表格；小屏允许横向滚动，不删除列。
- **图解**：优先使用语义 HTML + CSS；复杂 SVG 必须带文字说明。图示颜色仍取 stone-ink token。
- **交互**：只有筛选、折叠或图解确有必要时才用少量原生 JS；核心内容在 JS 失败时仍可读。
- **状态**：统一使用 `.status`，不要每种文档发明不同 badge 风格。
- **证据**：引用、代码、路径和数据紧邻结论，不把重要约束藏在 hover 或折叠区。

## 自检

生成后逐项检查：

- [ ] reference 只有 `html-page`，主题只有 `stone-ink`
- [ ] 页面壳、token、字体和组件来自本文件
- [ ] 一个 H1，开头有结论或 TL;DR
- [ ] 正文行宽可读，宽内容没有被压进窄栏
- [ ] `file://` 可打开；关键内容不依赖外网或 JS
- [ ] 移动端无横向页面溢出（宽表/代码可在自身容器滚动）
- [ ] 未手写 catalog 回链，未修改根 `index.html`

## 不要

- 因为内容是 spec、架构图或技术文档就切换另一套 reference / 主题。
- 先写 `.md` 再转换（除非命中 baoyu 显式口令）。
- 紫渐变 + Inter 灰卡片、营销 landing page、居中大 hero、每段一卡。
- 为追求「统一」把所有内容都压成同一种卡片；统一的是视觉语言，不是信息结构。
- 外链未说明的字体、图标或框架；引用 skill 目录里的运行时资源。
