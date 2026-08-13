# pretty-view 使用文档（人类阅读）

> 本文档面向人：说明 pretty-view 门卫 skill 的设计、用法与维护。
> 它**不随 sync 分发**（sync 只拷贝 `SKILL.md` 和 `references/`），也**不应被 skill/模型引用加载**；agent 侧行为以 `SKILL.md` 为准。

## 1. 为什么做门卫

直接给 agent 装 baoyu / html-ppt / html-slides 的问题：每份 description 都可能自动触发，且一次可能加载多个大 SKILL。门卫把展示能力收成单一入口：

```
用户点名 pretty-view，或明确要「展示/呈现」
     ↓
  pretty-view（门卫）
     ↓ 推断或确认介质：HTML / Markdown
  HTML → Read 某一个 refer skill → 执行 → 用完即弃
  Markdown → 内置准则，不加载 refer
```

## 2. 架构

refer skill 在 `references/`，由 `scripts/agents/sync.py` 随 `SKILL.md` 原样分发。它们不在 agent 的一级 skill 注册路径上，**不会独立触发**。第三方快照一般不修改；升级走第 6 节。

## 3. 触发

用户说「用 pretty-view」，或明确要把文档 / 知识 / 报告 / code review / 方案做成漂亮的 HTML 或 Markdown。普通写方案、做 review 不触发。

## 4. 门禁

| 门禁 | 防什么 |
|------|--------|
| 门 1 · 收窄触发 | 日常写作被当成「展示」 |
| 门 2 · 先定介质 | HTML/Markdown 猜错；未定介质就拖进大 refer |
| 门 3 · HTML 一次一个 refer | 上下文膨胀；ppt 与 slides 抢路由 |
| 门 4 · 产物不写进 references/；默认 `docs/pretty-view/` | 污染快照；落盘散落 |

介质与路由规则写在 `SKILL.md`：**强信号自动推断，不明确必须确认。**

## 5. refer skill 清单（2026-08）

| references/ 目录 | 场景 | 来源 |
|------------------|------|------|
| `baoyu-markdown-to-html` | 长文阅读页、公众号风格 HTML、md → 带内联 CSS 的 HTML | `jimliu/baoyu-skills` |
| `html-ppt` | 静态 HTML PPT（主题/布局/演讲者模式）；未点名 reveal.js 时的默认幻灯片 | `lewislulu/html-ppt-skill` |
| `html-slides` | reveal.js 交互式幻灯片（CDN） | `claude-office-skills/skills` |

commit 与审计说明见 `references/UPSTREAM.md`。

Markdown 展示没有第三方 refer，走 `SKILL.md` 内置准则。

## 6. 升级 / 新增 refer skill

```bash
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
git clone --depth 1 <上游仓库 URL> "$AUDIT_DIR/src"
bash <dotfiles>/agents/skills/skills-store/scripts/audit-skill.sh "$AUDIT_DIR/src/<skill 目录>"

rm -rf agents/skills/pretty-view/references/<name>
cp -a "$AUDIT_DIR/src/<skill 目录>" agents/skills/pretty-view/references/<name>
# 更新 references/UPSTREAM.md；html-ppt 继续排除 docs 动图与 scripts/verify-output
rm -rf "$AUDIT_DIR"
scripts/agents/sync.sh all
```

新增时同步改 `SKILL.md` 路由表与本文第 5 节。MIT License 中 `without limitation` 可能误报 `jailbreak_role`，对照 `UPSTREAM.md` 处理。

## 7. 默认落盘

未指定路径且需要落盘时，写到当前项目 `docs/pretty-view/<kind>/<slug>`。

- `docs/pretty-view/`（或用户指定路径）**已存在 → 直接写**；**不存在 → 先确认再创建**。
- 根下只放 `INDEX.md` 与可选 `_assets/`；正文按 kind 分目录（`articles` / `knowledge` / `reports` / `proposals` / `reviews` / `slides`）。
- 每写一篇更新 `INDEX.md`，保持链接可点。明确只要对话里看则不落盘。

细则在 `SKILL.md`「落盘」节。

## 8. 维护

| 要做什么 | 改哪里 |
|----------|--------|
| 门禁、介质推断、路由、落盘、Markdown 准则 | `agents/skills/pretty-view/SKILL.md`，然后 `scripts/agents/sync.sh all` |
| 升级/新增/移除第三方 refer | 第 6 节 + 路由表 + 本文第 5 节 |
| 项目偏好 | 项目根 `.pretty-view.md`（可选） |
