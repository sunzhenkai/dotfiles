# 结果

- status: applied
- applied_at: 2026-08-30 12:16 (UTC+8)

## 实际改动

`references/diagrams.md` 整份重写措辞层，行数仍为 53，结论未变。

| 原表述 | 现表述 |
|--------|--------|
| 不要用手绘 SVG/Mermaid 冒充 archify 产物 | 手绘不算 archify 产物——记法和校验规则不同，混进来的图下一轮没法再被 validate |
| 禁止把 INDEX 写成待办清单 | 空表是诚实的；写成待办清单会让读者以为有图可看 |
| 禁止为好看而发明拓扑 | 为了好看发明一条拓扑，等于把读者引向一个不存在的系统 |
| 不要用「没有图不算失败」跳过必配图 | 这句是给可省略的图留的余地，不适用于必配图；复杂逻辑缺图时读者只剩一份读不懂的流程 |
| 不要生成假 HTML | 生成假 HTML、或声称复杂逻辑已经讲清，比缺图更糟 |

## 验证

- `git apply --check --recount` / `git apply --recount`：通过
- `git diff --check`：无空白错误
- `python3 -m unittest discover`：50 tests OK，`test_diagrams_cover_complex_logic_without_fake_delivery` 依赖的四个标记均保留
- 强制性措辞（必须/禁止/不得/不要）密度：**19 处 → 3 处**，行数持平

## 偏差

无。patch 由 `difflib` 从真实文件生成，一次校验通过。

## 遗留

同类改写尚未覆盖 `routing.md`（46 行 14 处）与 `modes.md`（180 行 23 处）。
`modes.md` 承载三档粒度契约，改写前建议先有真实运行 eval 兜底，避免只凭读文本判断语义是否等价。
