---
id: pretty-view
name: pretty-view
description: 将已有文档、知识、报告、方案或 code review 做成有明确视觉方向的 Markdown、HTML 阅读页或演示文稿；负责判断单页、扁平多页或层级多页，并规定多页维护方式。仅在用户点名 pretty-view，或明确要求把内容做成漂亮的网页、阅读页、Markdown、HTML、PPT 或 slides 时使用；普通写作、方案和 code review 不触发。
---

# pretty-view（优雅展示门卫）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

本 skill 是展示路由器，不替用户写第一稿。固定流程：

```text
确认展示意图 → 确定介质 → 选择输出路径 → 判断页面架构
→ 建立内容与视觉 brief → 生成 → 视觉与链接验收 → 维护索引
```

普通 HTML 阅读页使用 `html-page` 约束信息架构与工程质量，并同时 Read `frontend-design` 形成与主题、受众和内容相符的视觉方向。统一的是可读性、导航、响应式、可访问性和维护合同，不是每篇页面的颜色与字体。

## 六道门禁

1. **门 1 · 收窄触发**：仅在用户点名 `pretty-view`，或明确要**展示/呈现**（做成网页、阅读页、PPT、slides、漂亮的 Markdown）时使用。用户只是在写方案、写文档、做 code review，不要加载。
2. **门 2 · 先定介质**：展示样式只有 **HTML** 和 **Markdown** 两种。按「介质推断」自动选择；不明确时必须向用户确认。介质未定时，禁止 Read `references/`。
3. **门 3 · HTML 再路由**：介质为 HTML 后，先核对专用路径的显式口令。未命中则 Read `references/html-page.md`，直写 HTML 阅读页。禁止因 `html`、技术分享、路演、小红书、公众号二字或「做成文档」就加载 baoyu / html-ppt / html-slides。
4. **门 4 · HTML 必做视觉设计**：进入任何 HTML 输出路径后 Read `references/frontend-design/SKILL.md`。它只负责视觉方向，不改变 `html-page` / PPT / slides / baoyu 的输出路径。先形成简短设计 brief，再写 HTML；禁止从固定皮肤或上一份产物无脑复制配色。
5. **门 5 · 产物不污染快照**：禁止写入 `references/` 下的第三方快照。`html-ppt` 的 `scripts/new-deck.sh` 默认在 skill 目录 `examples/` 落盘，**不要对 vendor 快照执行**；把所需 `assets/` 与模板拷到实际落盘目录，按相对路径引用。
6. **门 6 · 单介质**：默认只生成 Markdown **或** HTML 其中一种。选 HTML 不等于先写 `.md` 再转 HTML 并保留两份。把已有 Markdown 转成 HTML 须显式说明。

## 介质推断（HTML vs Markdown）

命中强信号直接采用，并用一句话告诉用户推断结果。只命中弱信号，或正反信号并存，必须确认。

| 介质 | 强信号 | 弱信号（需确认） |
|------|--------|------------------|
| **HTML** | 网页、HTML、浏览器打开、阅读页、md 转 html、PPT、幻灯片、slides、deck、keynote、reveal.js | 「展示一下」「做得好看」「做成文档」且未提格式；路演 / 小红书 / 公众号未点名排版或 PPT |
| **Markdown** | 明确说 markdown / md、笔记入库、PR / review 评论、贴到对话里看、不要 HTML | 「整理一下」「好看一点」且目标像仓库 `.md` 或聊天回复 |

确认时只问以下两项；两项互斥，默认只出选中的一种：

- ① Markdown（对话或 `.md` 文件，便于入库 / PR）— 只出 Markdown，不转 HTML
- ② HTML（浏览器打开的统一阅读页或幻灯片）— 只出 HTML，不另写一份 md 源稿

用户已指定扩展名时以扩展名为准。`.html` 与 `.md` 同时出现且未说「都要」时，再问只留哪一种。

## 单介质与 md→html 强门禁

`baoyu-markdown-to-html` 是已有 Markdown → 带样式 HTML（窄栏）的转换器。只在命中以下任一显式口令时使用：

- 「md 转 html」「markdown to html」「convert md to html」「把这份 markdown 转成 html」「把 md 转成阅读页」
- 点名 `baoyu` / `baoyu-markdown-to-html`
- 点名「公众号排版」「微信排版」（只说「公众号」不够）
- 点名仓库里已有的 `.md`，并明确说「转成 html / 转成 html 文件」

仅选择「② HTML」不够当成 md→html。默认阅读页必须**直写 HTML**，不要先落一篇新 `.md` 当源稿。

| 用户意图 | 落盘 | 生成方式 |
|----------|------|----------|
| HTML 阅读页，没说转换 | 只 `.html` | 直写统一 `html-page` 阅读页 |
| 只要 Markdown | 只 `.md` 或对话 | 内置 Markdown 准则 |
| 显式 md→html / baoyu / 公众号排版 | 只新增 `.html`；原 `.md` 留原处 | baoyu，以用户已有文件为输入 |
| 明确要 md 和 html 都留 | 才允许并存 | 只手改 md，HTML 由转换生成 |

## HTML 路由

### 专用路径显式口令

未列入的词（技术分享、路演、分享会、演讲、周报、pitch、小红书、做成文档、html、阅读页）一律不够。

| 显式口令（须用户亲口） | 路径 | Read |
|------------------------|------|------|
| 做 HTML PPT / 做一份 PPT / 幻灯片 / slides / deck / html-ppt / keynote / slideshow | `html-ppt` | `references/html-ppt/SKILL.md` |
| 点名 **reveal.js** / `html-slides` / 纵向嵌套幻灯片 | `html-slides` | `references/html-slides/SKILL.md` |
| md 转 html / convert md to html / 把这份 markdown 转成 html / 点名 baoyu / 公众号排版 / 微信排版 | `baoyu-markdown-to-html` | `references/baoyu-markdown-to-html/SKILL.md` |
| 以上都未命中，介质已是 HTML | `html-page` | `references/html-page.md` |
| 介质为 Markdown | 内置 Markdown 准则 | — |

只说「PPT」未点名 reveal.js → `html-ppt`。两类幻灯片口令同时出现时再问。`html-slides` 依赖 jsDelivr；离线或用户禁止外链时改走 `html-ppt` 并说明原因。

`frontend-design` 不属于输出路径；进入任一 HTML 路径后都叠加使用。它不能把阅读页改造成 landing page，也不能覆盖专用转换器的运行时约束。

### HTML 阅读页

所有未命中 PPT、reveal.js、显式 md→html 的 HTML 请求，无论是规格、RFC、PRD、问题对齐、技术文档、图解、对比、时间线、报告、方案、知识页或普通长文，都统一使用：

- **reference**：`html-page`
- **路径**：`references/html-page.md`
- **设计参考**：`frontend-design`
- **生成方式**：直写 `.html`

`html-page` 决定信息架构、页面关系和质量底线；`frontend-design` 决定本次视觉方向、字体、配色、布局特征和一个克制的记忆点。内容模式决定结构与组件：

| 内容模式 | 推荐结构 / 组件 |
|----------|-----------------|
| 规格 / RFC / PRD / 对齐 | 摘要 → 状态与元信息 → 需求/约束 → 决策 → 可追溯表 → 未决项 |
| 图解 / 对比 / 时间线 / 架构 | 摘要 → 图例 → `.diagram` / `.comparison` / `.timeline` → 证据与说明 |
| 技术文档 / 操作说明 | 摘要 → 元信息 → 分节正文 → callout → 表格 / 代码 / `kbd` |
| 报告 / 方案 / 知识 / 长文 | 结论 → 背景 → 要点 → 细节 → 风险 / 下一步 / 参考 |
| code review（仅用户显式要 HTML） | 范围与结论 → 按严重度发现 → 位置与证据 → 测试与残留风险 |

同一多页包必须共用一套 token、排版尺度、导航和组件语言；不同产物不必长得一样。默认不外链 JS 框架。

### 页面架构：单页、扁平多页、层级多页

先按内容边界和维护关系判断，不按字数机械拆页：

| 架构 | 何时使用 | 文件形态 | 导航 |
|------|----------|----------|------|
| **单页**（默认） | 同一主题、同一受众、顺序阅读、共同维护 | 一个 `.html` | 页内目录与锚点 |
| **扁平多页** | 多个可独立阅读的同级模块，没有真实父子关系 | `index.html` + 同级页面 + `_site.json` | 总览 + 全局同级导航 |
| **层级多页** | 内容存在稳定的“领域 → 子主题”关系，且需要分别维护或扩展 | `index.html` + 分组目录 + `_site.json` | 全局导航 + 面包屑 + 同级导航 |

以下情况才使用多页：用户明确要求；输入本来就是多个独立文档；模块需要独立分享、评审或发布；受众或维护周期明显不同。内容长、H2 多、含表格/代码/图解都不足以拆页。判断不确定时保持单页，不追问。

选择多页后再判断层级：

- 只是并列章节或附件 → 扁平多页，不制造层级。
- 能用稳定的“属于”关系描述，且每个父节点有自己的总览职责 → 层级多页。
- 只是阅读顺序、步骤先后或数量较多 → 仍是扁平结构，用排序表达，不建父子目录。
- 默认最多两级内容页；更深层级会显著增加定位与维护成本，除非用户明确要求文档站且内容确有稳定分类。

自动推断后用一句话告知：`按单页生成，使用页内目录组织。` 或 `检测到独立模块，采用扁平/层级多页：<页面地图摘要>。`

多页包合同：

1. `index.html` 是唯一对外入口；`_site.json` 是页面树、标题、顺序和父子关系的**唯一维护源**。
2. 所有页面使用 kebab-case 路径、相对 `href/src`，并能通过导航返回首页；禁止孤儿页、绝对磁盘路径和 `file:///...`。
3. 扁平多页的内容页放包根目录；层级多页按真实分类建目录，每个分组目录必须有 `index.html`。
4. 包内共用 `assets/` 中的 CSS/JS/图片；不要在每页复制一份会漂移的样式。关键内容在 JS 失败时仍可读。
5. 新增、删除、移动或改名页面时，按顺序更新：`_site.json` → 页面文件 → 首页/分组页 → 面包屑和前后页导航 → 链接检查。
6. 根 `INDEX.md` / catalog 只登记包的入口 `index.html`，不登记附属页。默认落盘根不存在或文件冲突时仍执行落盘门禁。

### 切换门禁

| 当前路径 | 禁止切到 | 除非用户 |
|----------|----------|----------|
| `html-page` 阅读页 | baoyu | 显式 md→html，或点名 baoyu / 公众号排版 / 微信排版 |
| `html-page` 阅读页 | `html-ppt` / `html-slides` | 显式要 PPT / 幻灯片 / slides / reveal.js |
| 幻灯片 | `html-page` 或 baoyu | 明确要文档/阅读页/不要翻页，或显式 md→html |
| baoyu / md→html | `html-page` 或 PPT | 明确不要转换，或显式要做 PPT |

「生成一个问题对齐文档，html」「做好看的技术文档」「技术分享 / 路演 / 小红书 + html」都走 `html-page`。只有「做一份 HTML PPT」或「把这篇 md 转成 html」才进入对应专用路径。

### 加载 refer 时的约束

- HTML 阅读页 Read `references/html-page.md` 与 `references/frontend-design/SKILL.md`；不得再搜索或拼接其他阅读页 reference。
- `{baseDir}` = 被 Read 的 vendor refer 目录，仅适用于 baoyu / html-ppt / html-slides。
- baoyu 仅在显式口令下使用。若其要求先跑未 vendor 的 `baoyu-format-markdown`，跳过并直接转换。脚本默认将 HTML 写在源 `.md` 同目录，转换后立刻移到目标路径；不要复制源 md。
- `html-ppt` 仅在显式口令下使用。只 Read 其 `SKILL.md` 与按需 `references/*.md`；把资源复制到落盘目录，不在快照里改模板。共享资源可放 `docs/pretty-view/_assets/`。
- `html-slides` 仅在显式点名 reveal.js / html-slides 时使用。
- 不要修改 `references/` 里的第三方快照；升级按同目录 `README.md` 操作。

## 视觉方向（一致但不套皮）

主题在路径已定后选择：

| 路径 | 默认主题 | 规则 |
|------|----------|------|
| `html-page` | 根据内容 brief 命名，如 `technical-field-notes` | 用 `frontend-design` 推导；同一多页包固定一套 token 与组件，不套固定主题 |
| `baoyu-markdown-to-html` | `simple` | 可推荐 `grace` / `modern`，生成前确认 |
| `html-ppt` | 技术分享 `tokyo-night`；正式汇报 `corporate-clean`；学术报告 `academic-paper`；小红书 `xiaohongshu-white` | 给 1 个推荐、至多 2 个备选，生成前确认 |
| `html-slides` | 技术分享 `night`；日间/文档 `white` | 可备选 `black` / `serif` / `moon`，生成前确认 |
| 内置 Markdown | — | 沿用仓库已有 Markdown 风格 |

同一项目优先沿用 `.pretty-view.md` 中明确且仍适合本次内容的偏好，但不得只因“以前用过”就复制。普通阅读页无需让用户先选主题；由内容 brief 推导并在交付时报告。多主题转换器不得静默随机选。

## 落盘（默认 `docs/pretty-view/`）

用户明确只要对话里看时不写文件。否则：

1. 用户指定路径就使用；未指定则默认 `docs/pretty-view/<kind>/<slug>`。
2. 目标路径或默认根已存在则直接写；不存在则先确认将创建的目录与文件名，确认前不 mkdir、不写文件。
3. 写入 `docs/pretty-view/` 时必须维护 `INDEX.md`；树里有 HTML 时还必须用脚本生成根 `index.html`。
4. INDEX 只登记实际落盘的介质。同一 slug 不得同时建 `.md` 与 `.html`，除非用户显式要求保留源稿。

### 层级

根下只放 `INDEX.md`、有 HTML 时的 `index.html` 与可选 `_assets/`。

| kind | 用于 |
|------|------|
| `articles` | 长文阅读页 |
| `knowledge` | 知识整理 |
| `reports` | 报告 |
| `proposals` | 方案 |
| `reviews` | code review |
| `slides` | PPT / 幻灯片 |

`<slug>` 使用 kebab-case。同名已存在时换 slug 或先问，禁止静默覆盖。

- 单文件：`docs/pretty-view/<kind>/YYYY-MM-DD-<slug>.html` 或 `.md`
- 多文件包：`docs/pretty-view/<kind>/YYYY-MM-DD-<slug>/`，包含 `index.html`、`_site.json`、内容页与可选 `assets/`
- 幻灯片一律用包：`docs/pretty-view/slides/<slug>/index.html`
- 根索引每个单文件或包只登记一行；包内附属页由主文件链接

### 索引

| 文件 | 用途 |
|------|------|
| `INDEX.md` | git / GitHub / 人读；登记 HTML 与 Markdown |
| `index.html` | 浏览器入口；只列 HTML 入口 |

维护顺序：

1. 先更新 `INDEX.md`，每个包或单文件一行。
2. 树里存在任意 HTML 产物时运行：

```bash
python3 <this-skill>/scripts/update-catalog.py docs/pretty-view
```

3. 仅有 Markdown 时不创建 `index.html`；删掉最后一篇 HTML 后同样运行脚本，让它移除空 catalog。
4. 交付 HTML 时首先告诉用户 `docs/pretty-view/index.html`，可附单篇入口，但不要罗列包内页面。

`<this-skill>` 是包含本 `SKILL.md` 的目录，不要假设脚本在当前项目根。脚本按 `INDEX.md` 与磁盘入口生成 catalog，并给非幻灯片入口注入「← 目录」回链。退出码 1 表示存在死链，修复后重跑。禁止手写根 `index.html` 或正文回链。

`INDEX.md` 示例：

```markdown
# pretty-view

浏览器入口：[index.html](index.html)。

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-14 | 鉴权方案 | proposals | HTML | [proposals/2026-08-14-auth.html](proposals/2026-08-14-auth.html) |
```

## 项目记录：`.pretty-view.md`（可选）

项目根的 `.pretty-view.md` 是偏好记录，不是路由依据。不存在时不主动创建；用户要求或首次成功使用后征得同意再写。只记元信息，不写密钥。建议格式：

```markdown
# pretty-view — <项目名>

## 使用记录

| 日期 | 介质 | reference | 主题 | 用于 | 效果/笔记 |
|------|------|-----------|------|------|-----------|
| 2026-08-14 | HTML | html-page + frontend-design | technical-field-notes | 技术方案 | 合适 |

## 偏好

- 默认介质：
- 默认 HTML 形式：`html-page`；用 `frontend-design` 按内容确定视觉方向
- 默认主题：
  - html-page：
  - baoyu-markdown-to-html：
  - html-ppt：
  - html-slides：
```

## 统一 HTML 阅读页准则

介质为 HTML 且未命中特殊路径时，必须 Read `references/html-page.md` 与 `references/frontend-design/SKILL.md` 并直写 `.html`。先确定主题、受众、页面任务和视觉 signature，再建立 token 与组件。多页包内复用同一设计系统；不同主题的独立产物应有自己的视觉身份。

共同技术要求：

- 完整可打开：`<!DOCTYPE html>`、`lang="zh-CN"`、viewport；`file://` 可用。
- 一个 H1；开头结论或 TL;DR；使用语义标签。
- 页面铺满视口；长正文保持可读行宽，宽表、代码、图和网格可使用宽内容区。
- 内联 CSS 或同目录相对资源；不要依赖 skill 目录，不默认外链 JS 框架。
- 不写营销 landing page，不使用紫渐变 + Inter 灰卡片，不为每个段落套卡片。
- 必须检查桌面与移动端；环境支持浏览器时截图复核构图、折行、溢出和视觉层级，发现模板感或布局问题后至少修正一轮。
- 不手写「← 目录」，不手改根 `index.html`。

## 内置 Markdown 准则

介质为 Markdown 时，先读项目已有 Markdown 风格并沿用。

### 结构

- 一个 H1；其余标题逐级递进。
- 开头给结论或 TL;DR（3–7 行），再展开。
- 对比、清单、评审意见用表格；流程用有序列表。
- 决策、风险、待确认用引用块或明确小标题。

| 类型 | 建议骨架 |
|------|----------|
| 文档 / 知识 | 结论 → 背景 → 要点 → 细节 → 参考 |
| 报告 | 结论 → 指标/发现 → 证据 → 建议 |
| 方案 | 目标与约束 → 推荐方案 → 备选与取舍 → 风险与下一步 |
| code review | 范围与结论 → 按严重度发现 → 测试与残留风险；每条含 `file:line` 与重要性 |

文风使用短句，一段一个意思；命令、路径、代码使用反引号；不写空话，不把展示做成第二份需求文档。只在对话里看时直接输出，不落盘。

## 边界

- 不自动触发普通写作或评审。
- HTML 一次只走一条输出路径：阅读页、baoyu、html-ppt、html-slides 四选一；`frontend-design` 是所有 HTML 路径的设计参考，不是输出路径。
- 默认只生成 Markdown / HTML 其中一种。
- 不修改第三方快照，不把密钥、内部 URL、公司代码贴进可公开产物。
- 本 skill 不替代内容创作 skill；输入应是已有草稿、仓库文件或本轮已生成正文。
- 大改已有展示页 / deck 前，先说明会动哪些文件。
- 面向用户回复的**最后一段**必须说明本次 reference 与主题。

## 交付结尾（MUST）

生成完成或只在对话给出展示后，最后一段固定写：

```text
本次使用
- reference: html-page + frontend-design
- 主题: <本次视觉方向名>
```

| 路径 | `reference` | `主题` |
|------|-------------|--------|
| HTML 阅读页 | `html-page` + `frontend-design` | 实际视觉方向名 |
| 显式 md→html / baoyu / 公众号排版 | `baoyu-markdown-to-html` | 实际 `--theme` 名 |
| 静态 PPT | `html-ppt` | 实际主题文件名 |
| reveal.js | `html-slides` | 实际 reveal 主题 |
| 内置 Markdown | `markdown`（内置准则） | `—` |

沿用偏好时在主题后加「（沿用项目偏好）」；用户本轮点名时加「（用户指定）」。
