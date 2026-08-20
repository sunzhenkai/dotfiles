---
id: pretty-view-ppt
name: pretty-view-ppt
description: 将已有文档、知识、报告或方案做成可用键盘演示的 HTML 演示文稿。仅在用户点名 pretty-view-ppt，或明确要求制作 PPT、幻灯片、slides、deck、keynote、slideshow、html-ppt、reveal.js 或 html-slides 时使用。
---

# pretty-view-ppt（HTML 演示文稿）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

本 skill 把已有内容做成 HTML 演示文稿，不替用户写第一稿。固定流程：

```text
确认演示意图 → 选择 html-ppt 或 html-slides → 复制运行时资源
→ 按所选 reference 出稿 → 键盘/翻页验收 → 维护索引
```

两条路径由各自 reference 决定模板、主题和运行时，避免设计合同互相覆盖。

## 路径选择

| 用户意图 | 路径 | Read |
|----------|------|------|
| 做 HTML PPT / 做一份 PPT / 幻灯片 / slides / deck / html-ppt / keynote / slideshow | `html-ppt` | `references/html-ppt/SKILL.md` |
| 点名 **reveal.js** / `html-slides` / 纵向嵌套幻灯片 | `html-slides` | `references/html-slides/SKILL.md` |

默认使用 `html-ppt`。只有用户点名 reveal.js、`html-slides` 或纵向嵌套结构时才使用 `html-slides`；两类口令同时出现时再问。`html-slides` 依赖 jsDelivr，离线或禁止外链时使用 `html-ppt` 并说明原因。

## 生成合同

- `{baseDir}` = 被 Read 的 vendor refer 目录。
- `html-ppt`：只 Read 其 `SKILL.md` 与按需 `references/*.md`；把所需资源复制到当前产物包的 `assets/`，不在快照里改模板，也不依赖 skill 或根级共享目录。
- `html-slides`：按其 reference 生成完整 reveal.js 页面。
- 每次只服从所选路径的主题、模板和运行时约束，禁止跨路径拼接设计规则。
- `html-ppt` 的 `scripts/new-deck.sh` 默认写入 skill 目录 `examples/`，不要对 vendor 快照执行；在实际产物目录自行建立包。
- 不要修改 `references/` 里的第三方快照；升级按同目录 `README.md` 操作。

## 视觉方向

| 路径 | 默认主题 | 规则 |
|------|----------|------|
| `html-ppt` | 由 `html-ppt` 的主题与模板目录推荐 | 沿用其 token、模板和运行时 |
| `html-slides` | 由 `html-slides` 的 reveal 主题决定 | 沿用 reveal.js 主题与层级结构 |

用户在本轮明确给出且仍适合内容的偏好可以沿用，但不得只因“以前用过”就复制。

## 落盘（默认 `docs/pretty-view-ppt/slides/`）

用户明确只要对话里看时不写文件。否则：

1. 用户指定路径就使用；未指定则默认 `docs/pretty-view-ppt/slides/<slug>/`。
2. 目标路径或默认根已存在则直接写；不存在则先确认将创建的目录与文件名，确认前不 mkdir、不写文件。
3. 写入默认根时维护 `INDEX.md`，并用脚本生成根 `index.html`。
4. 演示文稿一律用包，所需 CSS、JS、字体与图片放在包内并使用相对路径。

`<slug>` 使用 kebab-case。同名已存在时换 slug 或先问，禁止静默覆盖。

- 演示文稿包：`docs/pretty-view-ppt/slides/<slug>/index.html`
- 根索引每个包只登记一行；包内附属页由主文件链接

### 索引

| 文件 | 用途 |
|------|------|
| `INDEX.md` | git / GitHub / 人读 |
| `index.html` | 浏览器入口；只列 HTML 入口 |

维护顺序：

1. 先更新 `INDEX.md`，每个 deck 一行。
2. 运行：

```bash
python3 <this-skill>/scripts/update-catalog.py docs/pretty-view-ppt
```

3. 交付时首先告诉用户 `docs/pretty-view-ppt/index.html`，可附该演示文稿的 `index.html`。

`<this-skill>` 是包含本 `SKILL.md` 的目录。退出码 1 表示存在死链，修复后重跑。禁止手写根 `index.html`。

`INDEX.md` 示例：

```markdown
# pretty-view-ppt

浏览器入口：[index.html](index.html)。

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-14 | 海洋图鉴分享 | slides | HTML | [slides/marine-life/index.html](slides/marine-life/index.html) |
```

## 边界

- 一次只走 `html-ppt` 或 `html-slides` 一条路径。
- 不修改第三方快照，不把密钥、内部 URL、公司代码贴进可公开产物。
- 大改已有 deck 前，先说明会动哪些文件。
- 交付时用一句话说明入口文件；主题只有在帮助用户继续维护时才补充，不要求固定尾注。
