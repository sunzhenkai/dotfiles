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
       └─ 其他全部 → html-page + frontend-design
                         先判断页面架构，再按内容建立视觉方向
```

PPT、reveal.js、baoyu 仍只认显式口令。技术分享、路演、小红书或只说 HTML 不足以进入这些专用路径。

## 2. HTML 阅读页设计

阅读页同时加载两个职责互补的 reference：

- `html-page`：信息架构、单页/多页判断、导航、维护与工程质量
- `frontend-design`：基于主题、受众和页面任务确定字体、配色、布局与视觉 signature
- 不为所有文档套同一张皮
- 同一个多页包必须共用设计系统；不同产物允许有各自的视觉身份

生成前必须形成简短视觉 brief，生成后在桌面和移动端做视觉复核；环境支持浏览器时使用截图检查并至少修正一轮。

### 单页与多页策略

阅读页默认单页。内容长、章节多或同时有图表/代码时，优先使用页内目录与锚点，不因此拆页。多页分两类：

- **扁平多页**：多个独立同级模块，没有真实父子关系。
- **层级多页**：存在稳定的“领域 → 子主题”关系，分组页有自己的总览职责；默认最多两级内容页。

多页包以 `_site.json` 作为页面标题、路径、顺序和层级的唯一维护源。`index.html` 是唯一对外入口；层级包的每个目录都有 `index.html`。页面变动按 `_site.json` → 文件 → 页面地图 → 导航/面包屑 → 链接检查的顺序维护，根 catalog 只登记包入口。

## 3. 门禁

| 门禁 | 防什么 |
|------|--------|
| 门 1 · 收窄触发 | 日常写作被当成展示 |
| 门 2 · 先定介质 | HTML / Markdown 猜错 |
| 门 3 · 专用路径只认显式口令 | 技术分享或 HTML 误进 PPT / baoyu |
| 门 4 · HTML 必做视觉设计 | 固定模板、无内容依据的配色和布局 |
| 门 5 · 产物不写进 references | 污染 vendor 快照 |
| 门 6 · 单介质 | 默认同时维护 `.md` 和 `.html` 两套正文 |

视觉规则：所有 HTML 路径都叠加 `frontend-design`，但它不改变输出路径。普通阅读页按内容推导视觉方向；多主题转换器仍须推荐并确认。交付结尾必须报告 reference 与实际视觉方向或主题。

## 4. reference / 生成路径

| 路径 | 场景 | 来源 |
|------|------|------|
| `references/html-page.md` | 所有普通 HTML 阅读页 | 本仓库第一方信息架构与工程合同 |
| `baoyu-markdown-to-html` | **仅显式** md→html / baoyu / 公众号或微信排版 | `jimliu/baoyu-skills` |
| `html-ppt` | **仅显式** HTML PPT / 幻灯片 / slides / html-ppt | `lewislulu/html-ppt-skill` |
| `html-slides` | **仅显式** reveal.js / html-slides | `claude-office-skills/skills` |
| `frontend-design` | 所有 HTML 路径的视觉设计参考 | `anthropics/claude-code` |

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
- 单文件用 `kind/YYYY-MM-DD-<slug>.html`；多文件包包含 `index.html`、`_site.json`、内容页和共享 `assets/`。
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
