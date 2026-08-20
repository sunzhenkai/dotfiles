# pretty-view-html tests

```bash
python3 tests/test_skill_contract.py
python3 tests/test_update_catalog.py
python3 tests/test_marine_life_outputs.py
python3 tests/test_beacon_ttl_outputs.py
```

`tests/` 不分发到各 agent。`references/` 与 `scripts/` 才随 skill 同步。

## marine-life 夹具

用同一份海洋生物源稿检查 HTML 阅读页的层级、时间线、表格、列表、页内导航，以及层级多页合同。这是人工生成产物的结构回归夹具，不代表测试能够执行或评估 agent 的实际生成过程。

| 路径 | 文件 |
|------|------|
| 源稿 | `fixtures/marine-life/SOURCE.md` |
| 清单 | `fixtures/marine-life/manifest.json` |
| html-page | `golden/marine-life/html-page.html` |
| html-page 层级多页 | `golden/marine-life/html-page-site/`（`_site.json` + 面包屑 + 同级翻页） |

重新生成时：以 `SOURCE.md` 为输入，按 `SKILL.md` 生成 HTML，不要改 vendor 快照。

## beacon-ttl 夹具

用同一虚构事故的两份源稿检查 `article` 报告（故障复盘）与 `review` 评审（热修复 code review）的单页合同。不覆盖多页导航。

| 路径 | 文件 |
|------|------|
| 复盘源稿 | `fixtures/beacon-ttl/SOURCE-postmortem.md` |
| 评审源稿 | `fixtures/beacon-ttl/SOURCE-review.md` |
| 清单 | `fixtures/beacon-ttl/manifest.json` |
| html-page 复盘 | `golden/beacon-ttl/postmortem.html` |
| html-page 评审 | `golden/beacon-ttl/fix-review.html` |

重新生成时：以对应 `SOURCE-*.md` 为输入，按 `SKILL.md` 生成 HTML，不要改 vendor 快照。
