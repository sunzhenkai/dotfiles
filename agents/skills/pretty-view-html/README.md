# pretty-view-html 使用文档（人类阅读）

> 本文面向维护者。它不随 sync 分发；agent 行为以 `SKILL.md` 为准。

## 1. HTML 阅读页设计

阅读页同时加载两个职责互补的 reference：`html-page` 负责信息架构、页面关系和工程质量，`frontend-design` 负责基于内容确定视觉方向。具体生成合同只在 `references/html-page.md` 维护，本 README 不复制规则清单。

## 2. reference

| 路径 | 场景 | 来源 |
|------|------|------|
| `references/html-page.md` | 所有普通 HTML 阅读页 | 本仓库第一方信息架构与工程合同 |
| `frontend-design` | 仅普通 HTML 阅读页的视觉设计参考 | `anthropics/claude-code` |

当前 vendor commit 与审计说明见 `references/UPSTREAM.md`。第三方快照不要直接修改。

## 3. 升级 vendor

```bash
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
git clone --depth 1 <上游仓库 URL> "$AUDIT_DIR/src"
bash <dotfiles>/agents/skills/skills-store/scripts/audit-skill.sh "$AUDIT_DIR/src/<skill 目录>"

rm -rf agents/skills/pretty-view-html/references/<name>
rsync -a --exclude '.git' "$AUDIT_DIR/src/<skill 目录>/" agents/skills/pretty-view-html/references/<name>/
# 更新 references/UPSTREAM.md
rm -rf "$AUDIT_DIR"
scripts/agents/sync.sh all
```

`html-page.md` 是第一方 reference，不走 vendor 升级。新增普通阅读页能力应优先扩展其内容模式或组件，不再引入平行阅读页 reference。

## 4. 默认落盘

未指定路径且需要落盘时写到 `docs/pretty-view-html/<kind>/<slug>`：

- 默认根不存在时先确认再创建。
- 根下只放 `INDEX.md`、`index.html` 与可选 `_assets/`。
- 单文件用 `kind/YYYY-MM-DD-<slug>.html`；多文件包包含 `index.html`、`_site.json`、内容页和共享 `assets/`。
- 每个单文件或包只在 `INDEX.md` 登记一行。
- 树里有 HTML 时运行 `scripts/update-catalog.py` 生成根 `index.html`。
- 现有 Markdown 可作为输入，但本 skill 只新增 HTML。

## 5. 维护索引

| 要做什么 | 改哪里 |
|----------|--------|
| 使用合同、页面架构、落盘、交付 | `agents/skills/pretty-view-html/SKILL.md` |
| 统一阅读页页面壳、token、组件、内容模式 | `agents/skills/pretty-view-html/references/html-page.md` |
| HTML catalog | `agents/skills/pretty-view-html/scripts/update-catalog.py` |
| catalog 测试 | `agents/skills/pretty-view-html/tests/test_update_catalog.py` |
| 路由契约测试 | `agents/skills/pretty-view-html/tests/test_skill_contract.py` |
| 阅读页展示夹具 | `agents/skills/pretty-view-html/tests/test_marine_life_outputs.py`、`tests/test_beacon_ttl_outputs.py` |
| vendor 清单与审计 | `agents/skills/pretty-view-html/references/UPSTREAM.md` |

修改后运行针对性测试，并用 `scripts/agents/sync.sh all --dry-run` 检查分发内容。
