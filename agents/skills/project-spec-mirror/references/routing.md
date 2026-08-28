# 更新路由：文件 → 页

源文件是 git 的变更单位，不是规格的阅读单位。`diff` 给出改了哪些路径；本文件规定如何把它们映射到已有金字塔/切面页。

update 必须跑 `$SPECCTL route`，用它的 JSON（模块命中、rename、unmapped、`not_built`）。不要手算、不要绕过 CLI。不得改回「一变更文件一详页」。`route` 只返回模块 README；知识层仍由 Agent 跟链接。

## 算法

对 `$SPECCTL diff` 的每一条（`status` / `path`，rename 另有 `from`）：

1. **Rename（`status` 为 `R`）**：用 `from` 找旧归属，把该模块文件表那一行改成 `path`。若已有 `notes/<from>.md`，改名为 `notes/<path>.md` 并更新真身。禁止当成删除 + 新增。
2. **文件表精确匹配** `path`（rename 则先匹配 `from`）→ 落入含该行的模块。
3. 未命中 → **最长前缀**匹配该模块 README「根」表第一列。
4. 仍未命中 → 记入 `unmapped`：并入最近模块或新建模块，不得丢弃，也不得为此建文件详页。
5. 从命中的模块 README **跟随已有链接** → 实体 / 处理线 / 切片 / 契约。只改被波及的页。`overview.md` 仅在模块地图或主路径变了才改。
6. 非代码、配置、测试：优先 `facets/source.md` 与相关契约/切片，其次才是模块表。

标题约定（与 [layout.md](layout.md) 一致，便于日后 CLI 解析）：「根」或 `Roots`；「文件」或 `Files`。不要靠扫全库反引号路径做路由（易误伤）。

无模块 README（刚 init 未 build）→ `route` 返回 `not_built: true`，全部 `unmapped`，进入 `build` 而不是硬编路由。

## 与切面的分工

| 变更像什么 | 优先改 |
|------------|--------|
| 领域包、入口、符号 | 模块 README 文件表；跟链接的实体/处理线 |
| 路由 / schema / 测试名 | 契约页与切片 |
| 配置、样本、SOURCE 证据 | `facets/source.md` |
| 放量、灰度 | `traffic.md`（无则写「无」） |

切片是垂直切口，穿过多个文件。不要为切片里的每个文件建页；入口文件成为热点的条件见 [modes.md](modes.md)。

## 维护时

- 每个模块 README 必须有「根」表与「文件」表，否则下一步 update 无法路由。
- 新增源文件：先落入某模块的根前缀，再补文件表一行。
- 源文件消失：文件表删行或标明废弃；不要默默删 `<!-- manual -->`。
- `<!-- manual -->` 块不得覆盖。
