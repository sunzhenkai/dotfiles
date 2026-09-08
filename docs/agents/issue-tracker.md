# Issue tracker: 本地 Markdown

本仓库的 issue 与 spec 以 markdown 文件存放在 `.scratch/`。

## 约定

- 每个功能一个目录：`.scratch/<feature-slug>/`
- spec 为 `.scratch/<feature-slug>/spec.md`
- 实现 ticket 每个一张文件，路径为 `.scratch/<feature-slug>/issues/<NN>-<slug>.md`，从 `01` 起编号，不要合并成单一 tickets 文件
- 分诊状态写在每张 issue 文件顶部附近的 `Status:` 行
- 评论与对话历史追加到文件末尾的 `## Comments` 标题下

## 当 skill 说「发布到 issue tracker」

在 `.scratch/<feature-slug>/` 下新建文件（目录不存在则创建）。

## 当 skill 说「读取相关 ticket」

读取所指路径上的文件。用户通常会直接给出路径或 issue 编号。

## Wayfinding 操作

供 `/wayfinder` 使用。**map** 是一份文件，每张 ticket 对应一个 **child** 文件。

- **Map**：`.scratch/<effort>/map.md`（Notes / Decisions-so-far / Fog 正文）。
- **Child ticket**：`.scratch/<effort>/issues/NN-<slug>.md`，从 `01` 起编号，问题写在正文。`Type:` 行记录 ticket 类型（`research` / `prototype` / `grilling` / `task`）；`Status:` 行记录 `claimed` / `resolved`。
- **Blocking**：顶部附近的 `Blocked by: NN, NN` 行。所列文件均为 `resolved` 时，该 ticket 才视为解锁。
- **Frontier**：扫描 `.scratch/<effort>/issues/`，找仍开放、已解锁、未被认领的文件；编号最小者优先。
- **Claim**：开工前把 `Status:` 设为 `claimed` 并保存。
- **Resolve**：在 `## Answer` 标题下追加答案，把 `Status:` 设为 `resolved`，再把上下文指针（摘要 + 链接）追加到 `map.md` 的 Decisions-so-far。
