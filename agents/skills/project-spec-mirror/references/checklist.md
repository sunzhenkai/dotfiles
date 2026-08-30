# 交卷前自检

镜像写完、准备给回执之前对照本表，只核对本轮真正涉及的组：init 不必看 update 那组。任一条不满足就先修输出。

本文件随 Skill 安装分发，是运行现场唯一能读到的自检表。源仓库里另有 `evals/cases.yaml` 的完整回归集，只在维护本 Skill 时使用。

## 安全与边界（每轮都核对）

- 密钥、token、password、AccessKey、连接串等**值**在镜像里写成 `<REDACTED>`，回执里说明省略了什么。字段名与注入方式可以照写。
- 没有自动 `git commit` 或 `push`。
- 只写入 `detect` / `status` 给出的 `spec_root`，没有碰 `openspec/`、目标源码、测试或构建文件。
- `vendor/`、`node_modules/`、submodule 与外来仓的文件没有进模块、文件表或 `notes/`。邻接系统只在 `context/` 记边界。
- `<!-- manual -->` 块原样保留。

## 状态机

- CLI 退出码 2 时原样报告了 `prompt` / `confirm_args`，等用户同意才用 CLI 给的参数重跑，没有自行扩权。
- 收尾走的是 `$SPECCTL finalize`（coverage 门禁 → 回写状态 → 复验，一条命令）。要分步排查而直接用 `set-sync --built` 时，自己补上前后的 `coverage` 与 `validate`。
- 非 Git 源的 `synced_commit` 仍是 `null`，没有伪造 commit 或分支 diff。
- `mode=concise` 时 `detail_level` 为 `null`；`detailed` 时是 `complete` / `important` / `lightweight` 之一。

## 粒度

- 详尽是在同一批页上写深，不是给每个源文件建页；没有新建 `files/`，也没有把路径里的 `/` 拍成 `__` 当页名。
- `important`：范围内文件都出现在文件表，`important_paths` 命中的写到完整逻辑（有序步骤、关键分支、成败如何结束、副作用），其余简述。
- `complete`：inventory 里每个文件都有模块归属；`modules/*/notes/` 至少 5 篇、覆盖至少 3 个模块，按 [modes.md](modes.md) 的 5 类触发条件枚举，至少 1 篇用 topic 命名。
- 测试方法只写覆盖意图，`complete` 也一样。
- `symbols` 的输出当候选用，没有据此声称方法覆盖完备。

## 路由与覆盖

- 每个模块 README 都有「根」表和「文件」表，标题就是「根」「文件」或 `Roots` / `Files`——`route` 靠这两个标题解析，改了名下一轮 update 会失去路由。
- update 改的页来自 `$SPECCTL route` 的结果，不是手算。`status=R` 改文件表里那一行的路径，不是删一行再加一行。
- 文件表改完跑了 `$SPECCTL coverage`；`enforce` 为真时 `missing` 已清空。

## 交付

- 恢复投影五层（`context` / `data` / `surface` / `runtime` / `build`）里适用的写到可恢复，不适用的写了判断证据，而不是留空。
- 复杂业务逻辑（分叉、补偿、状态机、跨模块时序、非平凡数据路径）有 archify HTML 并链回对应 `flows/` 页；archify 不可用时在回执里列为阻塞，没有生成假 HTML 或占位文字。
- `diagrams/INDEX.md` 只链已经存在的 `.html`。
- 给人读的页面用项目自己的语言：标题是项目名或该页主题，正文没有「Spec 镜像」「孪生规格」「不是 OpenSpec」这类制作过程用语。
- 回执含项目、`spec_root`、粒度、分支与 commit（非 Git 写无）、本轮阶段、改了哪些层。
