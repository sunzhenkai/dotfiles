# 编目成员支持 aliases：CLI 短名解析到正规 id

编目组成员映射在 `id` / `optional` 之外增加 `aliases: [<name>, ...]`。别名是 **CLI 解析层的短名**，不是第二套安装 id。

overlay、lock、Desired Set、安装目录仍只认正规 `id`。`dotf agents skill apply ppt` 与 `dotf skills -i ppt` 先解析到 `frontend-slides`，再按该 id 写 overlay / 调 npx。手写 overlay 里出现别名时，Desired Set 计算会收成正规 id。

约束（fail closed）：

- 别名与 skill id 同规则：非空、不含 `/`
- 不得与任何 skill id、group 名、或其他别名冲突
- 不得重复自身 id

名字解析顺序变为：**group → skill id 或 alias → 透传 npx**（仅 `dotf skills -i`）。group 与 id 同名仍优先 group。

schema 仍为 v3；映射合法键为 `id` / `optional` / `aliases`。

首个用例：第三方 `frontend-slides`（`optional: true`，别名 `ppt`）。审计脚本对模板文案（`act as decorative`）、deploy 注释（`--yes`）和 “Cookie-cutter” 有误报；复核后锁定 `9906a34`，不进默认安装。
