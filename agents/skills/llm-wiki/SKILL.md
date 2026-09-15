---
id: llm-wiki
name: llm-wiki
description: 在本地 Markdown 工作区整理并维护可累积的知识 wiki：把源文档摄入 typed 页面、按引用回答、重组结构并做健康检查。文件系统为真相源，不依赖 llmwiki 服务或 MCP。在用户要求整理知识、维护 wiki、ingest 本地文档、查询已有 wiki、lint/重组知识库，或点名 llm-wiki 时使用。不用于项目 spec 镜像或代码探索。
---

# LLM Wiki（本地文档）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

把本地文档**编译**成可累积的 Markdown wiki：摄入时交叉引用、标出矛盾、写入持久页面。下次提问读 wiki，而不是重新从源材料拼答案。

本 skill 只操作本地文件。不启动 llmwiki 应用，不调用 MCP。不依赖 llmwiki 服务、MCP 或 SQLite。

## 非目标

- 不安装、运行或包装 llmwiki 二进制 / Web / MCP。
- 不写软件项目 spec 镜像（交给 `project-spec-mirror`）。
- 不探索或修改业务源码（交给 `dotf-code-explore`）。
- 不编辑 `raw/` 中的源材料。
- 不自动 commit / push / `dotf agents` sync。
- 不要创建 `.llmwiki/`、`.obsidian/` 或任何应用私有目录。

## 阶段

用户点名 `{{slash:llm-wiki}}` 且首词命中下表时走该阶段；否则按意图推断，并用一行说明。写盘阶段在首次绑定前必须先 `guide` 或 `init`。

| 阶段 | 何时 | 写入 |
|------|------|------|
| `guide` | 了解工作区目标、结构、覆盖与缺口 | 只读 |
| `init` | 尚无 wiki 布局，或要把一堆本地文档收成 wiki | 确认后创建骨架 |
| `ingest` | 把文件、粘贴文本或对话编进 wiki | 确认范围后写 `wiki/` |
| `query` | 问 wiki 里已有的知识 | 默认只读；归档问答需确认 |
| `organize` | 合并重复、搬页、补交叉引用 | 先给方案，确认后改 |
| `lint` | 健康检查；可顺带修 error | 修 error 可直接做；warning 需说明 |

## 绑定 `WIKI_ROOT`

会话绑定一个工作区根目录 `{WIKI_ROOT}`。路径由用户给出，或在 cwd 发现既有布局后确认。

**既有布局**：`{WIKI_ROOT}/purpose.md` 与 `{WIKI_ROOT}/wiki/` 同时存在。

1. 用户指定了目录 → 绑定该目录。
2. cwd 已是既有布局 → 绑定 cwd，并报告路径。
3. 否则列出候选（cwd 下含大量 `.md` 但无 `wiki/`），请用户选择 **init** 或给出路径。确认前不写盘。

禁止猜测家目录或机器特例路径。

## 核心不变量

1. **`raw/` 只读。** 源文件修订应作为新来源加入，不改旧文件。
2. **`wiki/` 是 LLM 维护的知识层**，写入必须尊重 `purpose.md` 与 `rules.md`（缺失则明确说缺，不编造规则）。
3. **文件系统是真理源。** 搜索用目录列表与内容检索（`rg` / 读文件）；不要假设有 FTS 索引。
4. **先搜再写，写后回读。** 更新已有页必须先读全文，保留旧事实与旧 `sources`。
5. **`wiki/log.md` 仅追加。** 条目格式：`## [YYYY-MM-DD] action | description`。不重排、不删历史。
6. **系统页** `wiki/overview.md`、`wiki/index.md`、`wiki/log.md` 不可当业务页删除或移走。
7. **声称必须可追溯** 到 `raw/`、`wiki/sources/` 或本轮用户提供的材料。没有证据就写「wiki 尚未覆盖」，不要编造。
8. **摄入前做隐私自查。** 凭据、密钥、个人联系方式、内部主机名不写入 wiki；写成 `<REDACTED>` 并告知用户。

## 加载

进入阶段后 **只读该阶段详情**，不要预加载其它 reference。

| 阶段 | 进入时读取 |
|------|------------|
| `guide` / `init` | [references/layout.md](references/layout.md) |
| `ingest` | [references/ingest.md](references/ingest.md)；写页时再读 [references/page-types.md](references/page-types.md) |
| `query` | 本文件步骤已够；归档到 `wiki/queries/` 时再读 page-types |
| `organize` | [references/organize.md](references/organize.md)；写页时再读 [references/page-types.md](references/page-types.md)；改完读 [references/lint.md](references/lint.md) |
| `lint` | [references/lint.md](references/lint.md) |

确定性检查：

```bash
python3 <this-skill>/scripts/lint_wiki.py "{WIKI_ROOT}"
python3 <this-skill>/scripts/lint_wiki.py "{WIKI_ROOT}" --write-index
```

`<this-skill>` 是本 skill 安装目录。不要手写绝对家目录。

## `guide`

只读了解工作区。进入后读 [references/layout.md](references/layout.md) 的 `guide` 节。

## `init`

没有 `wiki/` 时 **必须先获得确认** 再创建。未确认则停止。确认 `{WIKI_ROOT}` 与研究/知识范围一句话。进入后读 [references/layout.md](references/layout.md)，按其中脚手架创建，再转 `ingest`。

## `ingest`

进入后读 [references/ingest.md](references/ingest.md)。写页时再读 [references/page-types.md](references/page-types.md)。

## `query`

1. 先读 `wiki/index.md`，再用 `rg` 搜别名、缩写、中英变体；不要只搜一次精确词。
2. 读最相关页面，综合回答并引用 `[[页面标题]]`。
3. 证据不足就明说。页面冲突则并列来源，不静默挑选。
4. 用户要求归档时，先说明将写入 `wiki/queries/`，确认后再写。

## `organize`

先给方案，确认前不改。进入后读 [references/organize.md](references/organize.md)；写页时再读 [references/page-types.md](references/page-types.md)。改完跑 lint。

## `lint`

进入后读 [references/lint.md](references/lint.md)。先修 error，warning 说明后处理或有意推迟。
