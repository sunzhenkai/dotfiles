# 路由

update 必须跑 `$SPECCTL route`。不要手算，不要一文件一页。

`inventory` / `diff` / `route` 忽略：gitignore、二进制、构建产物、密钥、`vendor/` `node_modules/`、嵌套 git / submodule、外来仓。这些路径不要当 `unmapped` 建能力。

无有效 source-map 行 → `not_built`，应先 `build`。

算法：rename 用 `from` 匹配并**回写** source-map 路径；否则精确匹配，再最长前缀。仍未命中 → `unmapped`：并入已有能力或写入 INDEX「未指定」，不得丢弃。`finalize` 在已有 `synced_commit` 时拒绝未消化的 `unmapped`。

| 变更像什么 | 改哪里 |
|------------|--------|
| 领域行为、状态机 | 能力 spec + 处理线 |
| 路由 / 消息名 | `agent/surface/` |
| 逻辑存储 | `agent/data/` + model |
| 邻接 / 鉴权 | `briefing/architecture.md` |
| compose / 工具链 | 默认忽略 |
