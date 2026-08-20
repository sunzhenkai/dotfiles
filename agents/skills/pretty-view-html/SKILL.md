---
id: pretty-view-html
name: pretty-view-html
description: 将已有文档、知识、报告、方案或 code review 做成有明确视觉方向的 HTML 阅读页，并判断单页、扁平多页或层级多页。仅在用户点名 pretty-view-html，或明确要求把已有内容做成网页、HTML、浏览器阅读页、漂亮的 HTML 文档或将现有 Markdown 转成 HTML 时使用。
---

# pretty-view-html（HTML 阅读页）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

本 skill 只把已有内容做成 HTML 阅读页，不替用户写第一稿。固定流程：

```text
确认已有内容与受众 → 判断页面架构 → 建立内容与视觉 brief
→ 直写 HTML → 视觉与链接验收 → 维护索引
```

## 使用合同

1. 只 Read `references/html-page.md` 与 `references/frontend-design/SKILL.md`。
2. `html-page` 决定内容模式、信息架构、页面关系和工程底线；`frontend-design` 决定本次视觉方向。
3. 直接生成 `.html`。现有 `.md` 只是输入，不另建或改写 Markdown 副本，也不调用通用 Markdown 转换器。
4. 禁止写入 `references/`；第三方快照只按 `README.md` 的升级流程维护。
5. 用户只说“展示一下”“做得好看”但没有指定网页或 HTML 时，先确认输出格式。

## 页面架构

按 `references/html-page.md` 判断单页、扁平多页或层级多页。默认单页；篇幅长、标题多、含表格、代码或图解都不足以拆页。

多页包以 `_site.json` 作为页面清单和导航一致性的规范依据。修改后必须检查本地链接、页面清单与导航一致性。自动推断后用一句话告知页面架构。

## 视觉方向

写代码前按内容建立 Subject、Audience、Page job、Direction、Tokens、Layout、Signature brief。颜色、字体和布局从内容语义、阅读环境、对比度与可读性推导，不预设冷暖色系。普通请求无需让用户先选主题；同一多页包固定一套 token、组件和交互语言，不使用固定皮肤。

## 落盘（默认 `docs/pretty-view-html/`）

用户明确只要对话里看时不写文件。否则：

1. 用户指定路径就使用；未指定则默认 `docs/pretty-view-html/<kind>/<slug>`。
2. 目标路径或默认根已存在则直接写；不存在则先确认将创建的目录与文件名，确认前不 mkdir、不写文件。
3. 写入默认根时维护 `INDEX.md`，并用脚本生成根 `index.html`。
4. 根下只放 `INDEX.md`、`index.html` 与可选 `_assets/`。

| kind | 用于 |
|------|------|
| `articles` | 长文阅读页 |
| `knowledge` | 知识整理 |
| `reports` | 报告 |
| `proposals` | 方案 |
| `reviews` | code review |

`<slug>` 使用 kebab-case。同名已存在时换 slug 或先问，禁止静默覆盖。

- 单文件：`docs/pretty-view-html/<kind>/YYYY-MM-DD-<slug>.html`
- 多文件包：`docs/pretty-view-html/<kind>/YYYY-MM-DD-<slug>/`，包含 `index.html`、`_site.json`、内容页与可选 `assets/`
- 根索引每个单文件或包只登记一行；包内附属页由主文件链接

### 维护索引

1. 先更新 `INDEX.md`，每个包或单文件一行。
2. 运行：

```bash
python3 <this-skill>/scripts/update-catalog.py docs/pretty-view-html
```

3. 交付时首先告诉用户 `docs/pretty-view-html/index.html`，可附单篇入口，但不要罗列包内页面。

`<this-skill>` 是包含本 `SKILL.md` 的目录。脚本按 `INDEX.md` 与磁盘入口生成 catalog，并给入口页注入「← 目录」回链。退出码 1 表示存在死链，修复后重跑。禁止手写根 `index.html` 或正文回链。

`INDEX.md` 示例：

```markdown
# pretty-view-html

浏览器入口：[index.html](index.html)。

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-14 | 鉴权方案 | proposals | HTML | [proposals/2026-08-14-auth.html](proposals/2026-08-14-auth.html) |
```

## 最低要求

- 完整文档包含 doctype、准确 `lang`、charset、viewport 与 title。
- 可通过 `file://` 打开；本地资源只用产物目录内相对路径。
- 一个 H1，标题层级连续；需要非线性查找的长文有可点击目录，目录栏支持键盘可操作的视觉隐藏，隐藏后释放侧栏空间并保留恢复入口。
- 连续正文保持可读行宽；宽表、代码、图和网格使用受限宽内容区。
- Mermaid、PlantUML、Graphviz/DOT、D2 等文本定义图保留源码并渲染为本地图片；查看时支持图片/代码切换，默认显示图片。
- 响应式、打印、减少动效和 JS 失败降级可用。
- 生成后检查桌面与移动端视觉、本地链接和可访问性；发现问题就修正并复核。
- 不修改第三方快照，不把密钥、内部 URL、公司代码贴进可公开产物。
- 大改已有展示页前，先说明会动哪些文件。
