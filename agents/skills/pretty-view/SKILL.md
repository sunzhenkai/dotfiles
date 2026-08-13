---
id: pretty-view
name: pretty-view
description: 把文档、知识、报告、code review、方案等以优雅的 HTML 或 Markdown 展示；按意图路由到内置 references/ 下的 baoyu-markdown-to-html、html-ppt、html-slides，或走 Markdown 内置准则。默认只生成 Markdown 或 HTML 其中一种；把已有 md 转成 html 须用户显式说明，不要先写源稿再转并两份都留。用户点名 pretty-view，或明确要求展示/呈现/做成漂亮的网页、阅读页、PPT、slides 时使用。普通写文档、写方案、做 code review 本身不要加载本 skill。
---

# pretty-view（优雅展示门卫）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

本 skill 是**路由器**：把已有内容做成好看的展示，不负责替用户写第一稿。被触发后：推断或确认 **介质（HTML / Markdown）** → 若 HTML，再 Read `references/` 下某一个 refer skill 执行；若 Markdown，走文末内置准则。refer skill 已随分发到位，**无需额外安装**；它们不在 agent 的 skill 注册路径上，不会被独立自动触发。

## 五道门禁

1. **门 1 · 收窄触发**：仅在用户点名 `pretty-view`，或明确要**展示/呈现**（做成网页、阅读页、PPT、slides、漂亮的 Markdown）时使用。用户只是在写方案、写文档、做 code review，不要加载。
2. **门 2 · 先定介质**：展示样式只有 **HTML** 和 **Markdown** 两种。按下方「介质推断」自动选择；**不明确时必须向用户确认，禁止猜测。** 介质未定时，禁止 Read 任何 refer skill。
3. **门 3 · HTML 再路由**：介质为 HTML 后，按「HTML 路由表」选一个 refer skill。多条都沾边时再问用户。一次只 **Read** 一个 refer skill 的 `SKILL.md`，按其指引执行；用完即弃。
4. **门 4 · 产物不污染快照**：落盘规则见下节。**禁止**写入 `references/` 下的第三方快照。`html-ppt` 的 `scripts/new-deck.sh` 默认在 skill 目录 `examples/` 落盘，**不要对 vendor 快照执行**；把 `assets/` 与所选模板拷到落盘目录，按相对路径引用。
5. **门 5 · 单介质**：默认只生成 Markdown **或** HTML 其中一种（`INDEX.md` / `index.html` 是目录，不算正文）。选 HTML ≠ 先写一份 `.md` 再转 html 并两份都留。把已有 Markdown 转成 HTML 须显式说明，见「单介质与 md→html 强门禁」。

## 介质推断（HTML vs Markdown）

命中**强信号**→ 直接采用，并用一句话告诉用户推断结果。只命中弱信号、或正反信号并存 → **必须确认**。

| 介质 | 强信号 | 弱信号（需确认） |
|------|--------|------------------|
| **HTML** | 网页、HTML、浏览器打开、公众号、阅读页、md 转 html、PPT、幻灯片、slides、deck、路演、keynote、reveal.js、小红书图文 | 「展示一下」「做得好看」「做成文档」且未提格式 |
| **Markdown** | 明确说 markdown / md、笔记入库、PR / review 评论、贴到对话里看、不要 HTML | 「整理一下」「好看一点」且目标像仓库 `.md` 或聊天回复 |

确认时只问这两项（可一次问完）；两项互斥，默认只出选中的那一种：

- ① Markdown（对话或 `.md` 文件，便于入库 / PR）— 只出 Markdown，不转 HTML
- ② HTML（浏览器打开的阅读页或幻灯片）— 只出 HTML，不另写一份 md 源稿

用户已指定文件扩展名（`.html` / `.md`）时，以扩展名为准。两种扩展名都出现且未说「都要」→ 再问只留哪一种。

「md 转 html」是 HTML **介质**的强信号，同时命中下一节的转换门禁：输入必须是用户已有的 Markdown，不要再写一份新 md。

## 单介质与 md→html 强门禁

**默认只交一种产物。** 选 HTML → 只落 `.html`（或只在对话给 HTML）；选 Markdown → 只落 `.md` 或只在对话输出。禁止默认同篇同时写入 `.md` 和 `.html`。

`baoyu-markdown-to-html` 的 CLI 入口是已有 Markdown → 带样式 HTML。这是**转换器**，不是「HTML 阅读页」的默认两步工作流（先落盘源稿再生成阅读页）。

### 何时才把用户侧的 Markdown 当转换源

须用户**显式说明**（命中任一即可），否则不当成 md→html 任务：

- 「md 转 html」「markdown to html」「convert md to html」「把 md 转成阅读页」
- 点名仓库里已有的 `.md` 文件，并要求做成 HTML / 阅读页 / 公众号排版
- 「把这份 markdown 转成 html」

仅勾选确认项「② HTML（浏览器打开的阅读页）」**不够**。那只是定介质。不够的话：不要先落盘一篇新 `.md` 当「源稿」，不要告诉用户「同目录还有 Markdown 源稿」。

| 用户意图 | 落盘 | 怎么用 baoyu |
|----------|------|----------------|
| 只要 HTML 阅读页（正文来自讨论 / 草稿，**没**说转 md） | 只 `.html` | 允许当实现细节：md 写到 `mktemp` 临时文件 → 转换 → html 移到落盘路径 → **立刻删除临时 md**。临时文件不得出现在 `docs/pretty-view/` |
| 只要 Markdown | 只 `.md` 或对话 | **禁止**加载 baoyu，禁止生成 `.html` |
| **显式** md→html | 只新增 `.html`；用户原有 `.md` 留在原处，**不复制**进 `docs/pretty-view/` | 用用户已有文件当 `<markdown_file>` |
| 亲口要「md 和 html 都留 / 保留源稿」 | 才允许并存 | 并存时只手改 md，html 由转换生成，不要两套手改正文 |

**反例（禁止）**：用户勾了 HTML 阅读页 → 把总结写成 `docs/pretty-view/knowledge/….md` → 再转成同名 `.html` → 两份都提交，并说「Markdown 是源、HTML 是生成物」。

## HTML 路由表（意图 → refer skill）

路径相对本 SKILL.md 所在目录。

| 用户意图 | refer skill | 路径 |
|----------|-------------|------|
| 长文阅读页（只要 HTML）：文档、知识、报告、方案正文、公众号排版 | `baoyu-markdown-to-html` | `references/baoyu-markdown-to-html/SKILL.md` |
| **显式**把已有 Markdown 转成带样式 HTML（须命中转换口令或点名已有 `.md`） | `baoyu-markdown-to-html` | `references/baoyu-markdown-to-html/SKILL.md` |
| 静态 HTML PPT / 路演 / 分享会 / 演讲者模式 / 小红书图文（默认幻灯片） | `html-ppt` | `references/html-ppt/SKILL.md` |
| 明确要 **reveal.js**、交互式 fragments、纵向嵌套幻灯片、单文件 CDN 演示 | `html-slides` | `references/html-slides/SKILL.md` |
| 介质为 Markdown，或不外加载 HTML refer | 内置 Markdown 准则（见文末） | — |

两行都走同一个 refer：差别在输入（临时 md vs 用户已有 md）和产物（默认只留 html）。不要因为走了 baoyu 就再落一份 `.md`。

### 内容类型 → 默认（仅当介质已定为 HTML、形式未说清）

| 内容 | 默认 | 改口 |
|------|------|------|
| 文档 / 知识 / 长报告 / 方案（给人读） | `baoyu-markdown-to-html` | 用户说要汇报、路演、翻页 → `html-ppt` |
| 方案答辩、技术分享、周报演示、pitch | `html-ppt` | 用户点名 reveal.js → `html-slides` |
| code review | **默认走 Markdown**（PR 友好）；仅当用户要「给团队讲这次 review」才用 `html-ppt` | — |

`html-ppt` 与 `html-slides` 都做幻灯片：**未点名 reveal.js 时默认 `html-ppt`**（自带主题/布局/演讲者模式，不依赖 reveal.js CDN）。两者都沾边时必须再问。

### 加载 refer 时的约束

- `{baseDir}` = 被 Read 的那个 refer 目录（含 `SKILL.md` 的那一层），不是当前 git 仓库根。
- `baoyu-markdown-to-html` 若要求先跑 `baoyu-format-markdown`：本仓库未 vendor 该 skill，**跳过**，直接转换。脚本默认把 HTML 写在源 `.md` 同目录 → **转完立刻把 html 移到落盘路径**，不要把展示产物留在源旁或 `references/`。用户只要 HTML 时，源 md 必须是临时文件并在移走 html 后删除，**不要**在 `docs/pretty-view/` 留下 `.md`。
- `html-ppt`：只 Read 其 `SKILL.md` 与按需的 `references/*.md`；主题/布局从 `assets/`、`templates/` 复制到落盘目录，不在快照里改模板。共享静态资源放到 `docs/pretty-view/_assets/`（已有则复用）。
- `html-slides` 依赖 jsDelivr 上的 reveal.js；离线或用户禁止外链时改走 `html-ppt`，并说明原因。
- 不要修改 `references/` 里的第三方文件；升级走重新 vendor（见同目录 `README.md`）。

## 落盘（默认 `docs/pretty-view/`）

用户**明确不要落盘**（只要对话里看）→ 不写文件。除此之外：

1. **路径**：用户指定了就用指定路径；未指定则默认 `docs/pretty-view/<kind>/<slug>`（相对当前项目根）。
2. **存在性**：目标路径（指定路径，或默认根 `docs/pretty-view/`）**已存在 → 直接写入**；**不存在 → 先确认再创建**，说明将创建的目录与文件名。确认前不 mkdir、不写文件。
3. **索引**：凡写入 `docs/pretty-view/` 树，必须维护层级、`INDEX.md`，以及（有 HTML 时）`index.html`（见下）。写到该树以外时不强制建索引。
4. **单介质**：INDEX 只登记实际落盘的那种介质。不要给同一 slug 同时建 `.md` 和 `.html`，除非用户显式要求保留源稿。确认落盘路径时只报将创建的那一种文件（选 HTML 就只报 `.html`）。

### 层级

不要把产物堆在 `docs/pretty-view/` 根下（根上只放 `INDEX.md`、有 HTML 时的 `index.html`，以及幻灯片共享的 `_assets/`）。

| kind | 用于 |
|------|------|
| `articles` | 长文阅读页（baoyu HTML） |
| `knowledge` | 知识整理 |
| `reports` | 报告 |
| `proposals` | 方案 |
| `reviews` | code review |
| `slides` | PPT / 幻灯片（`html-ppt` / `html-slides`） |

`<slug>`：kebab-case，取自标题；同名已存在则换 slug（加后缀）或先问，禁止静默覆盖。同 slug 不要同时建 `.md` 和 `.html`，除非用户显式要求保留源稿。

**一次一个文件** → 扁平：

`docs/pretty-view/<kind>/YYYY-MM-DD-<slug>.html` 或 `.md`

**一次多个文件**（多篇阅读页、正文+附属页、幻灯片、html + 局部资源等）→ 同名文件夹：

`docs/pretty-view/<kind>/YYYY-MM-DD-<slug>/`

- 主文件固定为 `index.html`（主文档 / 封面；多篇对等时由它做包内目录）。Markdown 包则用 `index.md`。
- 其余文件放在同一文件夹内，由**主文件**链过去（包内路由）。
- 根目录 `INDEX.md` / `index.html` **只登记这一份主文件**，不要把包内每一页都加进去。
- 幻灯片一律走包：`docs/pretty-view/slides/<slug>/index.html`（可带日期前缀），资源指向 `../../_assets/` 或目录内相对路径。

禁止：把一次生成的多篇 HTML 平铺在 kind 目录下，再逐篇写进根索引。

### 索引

两份目录，职责不同。缺 `index.html` 时，浏览器 / `file://` / 静态服务器没有入口，生成的 HTML 就是死链。

| 文件 | 给谁 | 内容 |
|------|------|------|
| `INDEX.md` | git / GitHub / 人读 | 全部条目（HTML 与 Markdown） |
| `index.html` | **浏览器入口** | 只列出 HTML **入口**（扁平文件或包内 `index.html`） |

维护顺序（写入 `docs/pretty-view/` 树时 **MUST**）：

1. 先改 `INDEX.md`：**每个包或每个单文件只一行**（首次不存在则创建）。类型用上表 kind。多文件包的路径指向主文件 `…/<slug>/index.html`，不要为包内附属页各加一行。
2. 只要树里存在任意 HTML 产物（不含 `_assets/`、不含根上这份 catalog）：立刻跑 catalog 脚本，**禁止手写/重设计** `index.html`。
3. 仅 Markdown、树里没有任何 HTML 时：不创建 `index.html`。删掉最后一篇 HTML 后同样跑脚本（脚本会去掉 catalog，避免指向空页）。
4. 交付 HTML 时把 `docs/pretty-view/index.html` 当作入口告诉用户；单篇/主文件路径可以附上，但不能只给单篇、也不能罗列包内每一页。

```bash
python3 <this-skill>/scripts/update-catalog.py docs/pretty-view
```

`<this-skill>` 是含本 `SKILL.md` 的目录（安装后常见于 `~/.cursor/skills/pretty-view/` 或项目 `.claude/skills/pretty-view/` 等）。**不要**假设脚本在当前仓库根下。脚本会：按 `INDEX.md` + 磁盘上的**入口** HTML（kind 下扁平文件，或包目录里的 `index.html`）生成根 `index.html`；包内其他 HTML 不进根目录、也不当孤儿；给阅读页主文件注入「← 目录」回链（幻灯片不注入）；INDEX 漏登记某个入口会警告并补上。退出码 1 = INDEX 里有指向不存在文件的死链，先补文件或改 INDEX 再重跑。

```markdown
# pretty-view

浏览器入口：[index.html](index.html)。

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-13 | 鉴权方案 | proposals | HTML | [proposals/2026-08-13-auth.html](proposals/2026-08-13-auth.html) |
| 2026-08-13 | 鉴权系列 | proposals | HTML | [proposals/2026-08-13-auth-series/index.html](proposals/2026-08-13-auth-series/index.html) |
```

不要另起平行 README 当第二份目录；需要说明用法时在 INDEX 文首写一小段即可。

## 项目记录：`.pretty-view.md`（可选）

项目根的 `.pretty-view.md` 是给人看的偏好记录，不是路由依据。不存在时不主动创建；用户要求，或某 refer 首次成功使用后征得同意再写。只记元信息，不写密钥。

```markdown
# pretty-view — <项目名>

## 使用记录

| 日期 | 介质 | refer skill | 用于 | 效果/笔记 |
|------|------|-------------|------|-----------|
| 2026-08-13 | HTML | html-ppt | 技术方案分享 | tokyo-night 合适 |

## 偏好

- 默认介质：
- 默认 HTML 形式：阅读页 / 幻灯片
```

## 内置 Markdown 准则（兜底）

介质为 Markdown，或用户选择不外加载 HTML refer 时使用。先读项目已有 Markdown 风格（标题层级、callout、表格习惯）并沿用。

### 结构

- 一个 H1；其余按层级递进，不跳级。
- 开头给结论或 TL;DR（3–7 行），再展开。
- 对比、清单、评审意见用表格；流程用有序列表。
- 决策 / 风险 / 待确认用引用块或明确小标题，不埋进段落。

### 按内容类型

| 类型 | 建议骨架 |
|------|----------|
| 文档 / 知识 | 结论 → 背景 → 要点 → 细节 → 参考 |
| 报告 | 结论 → 指标/发现 → 证据 → 建议 |
| 方案 | 目标与约束 → 推荐方案 → 备选与取舍 → 风险与下一步 |
| code review | 范围与结论 → 按严重度分组的发现（必须改 / 建议 / 可选）→ 测试与残留风险。每条发现含位置（`file:line`）与为何重要 |

### 文风

- 短句、可扫读；一段一个意思。
- 代码/命令/路径用反引号；大段代码用围栏并标明语言。
- 不写空话（「众所周知」「值得注意的是」）；不把展示做成第二份需求文档。

### 落点

- 只要对话里看 → 直接输出 Markdown，不落盘。
- 需要落盘 → 走「落盘」节（默认 `docs/pretty-view/`，维护 INDEX.md；有 HTML 时再维护 index.html）。
- 默认不同时落盘 `.md` 与 `.html`。仅当用户**显式**要求保留源稿时才并存；并存时 Markdown 是源、HTML 是生成物，不要两套手改正文。

## 边界

- 不自动触发普通写作/评审；一次只加载一个 HTML refer skill；**不修改** `references/` 下的第三方快照。
- 默认只生成 Markdown / HTML 其中一种；md→html 须显式说明（见「单介质与 md→html 强门禁」）。
- 不把密钥、内部 URL、公司代码贴进可公开的 HTML/PPT。
- 本 skill 不替代内容创作 skill；输入应是已有草稿、仓库文件或本轮已生成的正文。
- 大改已有展示页/deck 前，先说明会动哪些文件。
