# pretty-view-ppt tests

```bash
python3 tests/test_pretty_view_ppt_contract.py
python3 tests/test_update_catalog.py
python3 tests/test_marine_life_outputs.py
```

`tests/` 不分发到各 agent。`references/` 与 `scripts/` 才随 skill 同步。

## marine-life 夹具

用同一份海洋生物源稿检查 html-ppt 与 html-slides：层级、时间线、表格、列表是否还在，以及各路径的合同有没有被改坏。这是人工生成产物的结构回归夹具，不代表测试能够执行或评估 agent 的实际生成过程。

| 路径 | 文件 |
|------|------|
| 源稿 | `fixtures/marine-life/SOURCE.md` |
| 清单 | `fixtures/marine-life/manifest.json` |
| html-ppt | `golden/marine-life/html-ppt/index.html` |
| html-slides | `golden/marine-life/html-slides/index.html` |

重新生成时：以 `SOURCE.md` 为输入，按 `SKILL.md` 路由，不要改 vendor 快照。html-ppt 所需 CSS/JS 必须复制进自身 `assets/`，产物不得依赖 skill 的 `references/`。
