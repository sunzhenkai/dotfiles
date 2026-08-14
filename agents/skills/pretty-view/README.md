# pretty-view 使用文档（人类阅读）

> 本文面向维护者。它不随 sync 分发；agent 行为以 `SKILL.md` 为准。

## 1. 为什么做门卫

直接安装 baoyu / html-ppt / html-slides 会让多份 description 同时触发。pretty-view 把展示能力收成单一入口，并把普通阅读页进一步收敛为一套视觉系统：

```text
用户点名 pretty-view，或明确要展示/呈现
  ↓
推断或确认介质：HTML / Markdown
  ├─ Markdown → 内置准则
  └─ HTML
       ├─ 显式 PPT / 幻灯片 / html-ppt → html-ppt
       ├─ 显式 reveal.js / html-slides → html-slides
       ├─ 显式 md→html / baoyu / 公众号排版 → baoyu-markdown-to-html
       └─ 其他全部 → html-page + stone-ink
                         只按 spec / visual / doc / article / review 组合组件
```

PPT、reveal.js、baoyu 仍只认显式口令。技术分享、路演、小红书或只说 HTML 不足以进入这些专用路径。

## 2. 统一阅读页设计

过去规格、图解、技术文档和普通长文分别进入多套 reference，导致页面壳、token、字体和组件不一致。现在所有阅读页只 Read `references/html-page.md`：

- 唯一 reference：`html-page`
- 唯一默认主题：`stone-ink`
- 统一页面壳、排版、语义 token 和组件族
- 内容差异仅通过 `spec`、`visual`、`doc`、`article`、`review` 模式表达
- 图解、宽表、目录和少量交互仍可按需使用，但不再形成独立视觉系统

这保证同一项目生成的规格、方案、报告和技术说明看起来属于同一个产品，同时保留不同信息结构。

### 单页与多页策略

阅读页**默认单页**。内容长、章节多或同时有图表/代码时，优先使用页内目录与锚点，不因此拆页。只有命中强信号才自动拆页：用户明确要求多页；输入由多个独立文档构成；存在总览加至少两个独立查阅模块；或不同部分面向不同受众/维护周期。无法确定时保持单页，不向用户确认。

自动拆页不需要确认，但必须先用一句话告知推断结果和页面地图。多页包保持一层结构：`index.html` 是唯一根入口并链接全部附属页；附属页用相对路径返回主文件；所有页面继续使用 `html-page` / `stone-ink`。路径不存在或文件冲突仍走原有落盘确认门。

## 3. 门禁

| 门禁 | 防什么 |
|------|--------|
| 门 1 · 收窄触发 | 日常写作被当成展示 |
| 门 2 · 先定介质 | HTML / Markdown 猜错 |
| 门 3 · 专用路径只认显式口令 | 技术分享或 HTML 误进 PPT / baoyu |
| 门 4 · 产物不写进 references | 污染 vendor 快照 |
| 门 5 · 单介质 | 默认同时维护 `.md` 和 `.html` 两套正文 |

主题规则：`html-page` 固定使用 `stone-ink`；多主题路径（html-ppt / html-slides / baoyu）仍须推荐并确认。交付结尾必须报告 reference 与主题。

## 4. reference / 生成路径

| 路径 | 场景 | 来源 |
|------|------|------|
| `references/html-page.md` | 所有普通 HTML 阅读页 | 本仓库第一方统一设计系统 |
| `baoyu-markdown-to-html` | **仅显式** md→html / baoyu / 公众号或微信排版 | `jimliu/baoyu-skills` |
| `html-ppt` | **仅显式** HTML PPT / 幻灯片 / slides / html-ppt | `lewislulu/html-ppt-skill` |
| `html-slides` | **仅显式** reveal.js / html-slides | `claude-office-skills/skills` |

当前 vendor commit 与审计说明见 `references/UPSTREAM.md`。第三方快照不要直接修改。

## 5. 升级 vendor

```bash
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
git clone --depth 1 <上游仓库 URL> "$AUDIT_DIR/src"
bash <dotfiles>/agents/skills/skills-store/scripts/audit-skill.sh "$AUDIT_DIR/src/<skill 目录>"

rm -rf agents/skills/pretty-view/references/<name>
rsync -a --exclude '.git' "$AUDIT_DIR/src/<skill 目录>/" agents/skills/pretty-view/references/<name>/
# 更新 references/UPSTREAM.md
rm -rf "$AUDIT_DIR"
scripts/agents/sync.sh all
```

`html-page.md` 是第一方 reference，不走 vendor 升级。新增普通阅读页能力应优先扩展其内容模式或组件，不再引入平行阅读页 reference。只有具有明确不同介质/运行时的能力才考虑新专用路径。

## 6. 默认落盘

未指定路径且需要落盘时写到 `docs/pretty-view/<kind>/<slug>`：

- 默认根不存在时先确认再创建。
- 根下只放 `INDEX.md`、有 HTML 时的 `index.html` 与可选 `_assets/`。
- 单文件用 `kind/YYYY-MM-DD-<slug>.html`；多文件用 `kind/YYYY-MM-DD-<slug>/index.html`。
- 每个单文件或包只在 `INDEX.md` 登记一行。
- 树里有 HTML 时运行 `scripts/update-catalog.py` 生成根 `index.html`。
- 默认只落 `.md` 或 `.html` 一种；显式 md→html 才使用 baoyu。

## 7. 维护索引

| 要做什么 | 改哪里 |
|----------|--------|
| 门禁、介质推断、路由、主题、落盘、交付结尾 | `agents/skills/pretty-view/SKILL.md` |
| 统一阅读页页面壳、token、组件、内容模式 | `agents/skills/pretty-view/references/html-page.md` |
| HTML catalog | `agents/skills/pretty-view/scripts/update-catalog.py` |
| catalog 测试 | `agents/skills/pretty-view/tests/test_update_catalog.py` |
| 路由契约测试 | `agents/skills/pretty-view/tests/test_skill_contract.py` |
| vendor 清单与审计 | `agents/skills/pretty-view/references/UPSTREAM.md` |
| 项目偏好 | 项目根 `.pretty-view.md`（可选） |

修改后运行针对性测试，并用 `scripts/agents/sync.sh all --dry-run` 检查分发内容。
