# pretty-view-ppt 使用文档（人类阅读）

> 本文面向维护者。它不随 sync 分发；agent 行为以 `SKILL.md` 为准。

## 1. reference / 生成路径

| 路径 | 场景 | 来源 |
|------|------|------|
| `html-ppt` | **仅显式** HTML PPT / 幻灯片 / slides / html-ppt | `lewislulu/html-ppt-skill` |
| `html-slides` | **仅显式** reveal.js / html-slides | `claude-office-skills/skills` |

当前 vendor commit 与审计说明见 `references/UPSTREAM.md`。第三方快照不要直接修改。

## 2. 升级 vendor

```bash
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
git clone --depth 1 <上游仓库 URL> "$AUDIT_DIR/src"
bash <dotfiles>/agents/skills/skills-store/scripts/audit-skill.sh "$AUDIT_DIR/src/<skill 目录>"

rm -rf agents/skills/pretty-view-ppt/references/<name>
rsync -a --exclude '.git' "$AUDIT_DIR/src/<skill 目录>/" agents/skills/pretty-view-ppt/references/<name>/
# 更新 references/UPSTREAM.md
rm -rf "$AUDIT_DIR"
scripts/agents/sync.sh all
```

只有具有明确不同运行时的能力才考虑新专用路径。

## 3. 默认落盘

未指定路径且需要落盘时写到 `docs/pretty-view-ppt/slides/<slug>/`：

- 默认根不存在时先确认再创建。
- 幻灯片一律用包：`index.html` + 复制进产物包的 `assets/`，不能引用 skill 的 `references/`。
- 每个包只在 `INDEX.md` 登记一行。
- 写完后运行 `scripts/update-catalog.py` 更新根 `index.html`。

## 4. 维护索引

| 要做什么 | 改哪里 |
|----------|--------|
| 路径选择、生成合同、落盘、交付 | `agents/skills/pretty-view-ppt/SKILL.md` |
| HTML catalog | `agents/skills/pretty-view-ppt/scripts/update-catalog.py` |
| catalog 测试 | `agents/skills/pretty-view-ppt/tests/test_update_catalog.py` |
| 路由契约测试 | `agents/skills/pretty-view-ppt/tests/test_pretty_view_ppt_contract.py` |
| 演示夹具 | `agents/skills/pretty-view-ppt/tests/test_marine_life_outputs.py` |
| vendor 清单与审计 | `agents/skills/pretty-view-ppt/references/UPSTREAM.md` |

修改后运行针对性测试，并用 `scripts/agents/sync.sh all --dry-run` 检查分发内容。
