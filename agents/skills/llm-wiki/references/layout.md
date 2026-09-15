# 工作区布局

`{WIKI_ROOT}` 的 canonical 布局。`purpose.md` 与 `rules.md` 在工作区根，不在 `wiki/` 内。

```text
{WIKI_ROOT}/
├── purpose.md              # 目标、关键问题、范围（人与 LLM 共读）
├── rules.md                # 语言、引用、保留/脱敏规则
├── raw/
│   ├── sources/            # 不可变源文件（只读）
│   └── assets/             # 本地图片等资源（只读）
└── wiki/
    ├── overview.md         # 全局总览（系统页）
    ├── index.md            # 内容目录（系统页，ingest/organize/lint --write-index 后更新）
    ├── log.md              # 仅追加操作日志（系统页）
    ├── entities/           # 实体：人、组织、产品、项目
    ├── concepts/           # 概念：术语、方法、框架
    ├── sources/            # 源材料摘要（不是 raw 原件）
    ├── synthesis/          # 跨源综合
    ├── comparisons/        # 对比
    ├── queries/            # 归档问答
    └── templates/          # 系统模板，不是业务内容
```

Typed 子目录必须用**复数**：`entities/`，不是 `entity/`。

## 路径分类

| 类别 | 路径 | 规则 |
|------|------|------|
| 工作区配置 | `purpose.md`, `rules.md` | 根目录；缺失则说明，不编造 |
| 不可变源 | `raw/sources/`, `raw/assets/` | 只读；修订以新文件加入 |
| 系统页 | `wiki/overview.md`, `wiki/index.md`, `wiki/log.md` | 仅有的合法顶层 wiki Markdown |
| 业务页 | `wiki/entities/` … `wiki/queries/` | 必须落在 typed 子目录 |
| 系统模板 | `wiki/templates/` | init 脚手架；lint 不当地孤立业务页 |

## 反模式

| 错误 | 原因 |
|------|------|
| `wiki/purpose.md`, `wiki/rules.md` | 配置在工作区根 |
| `wiki/raw/` | 源目录是 `{WIKI_ROOT}/raw/` |
| `wiki/entity/`, `wiki/concept/`, `wiki/source/` | 应用复数目录名 |
| `wiki/skills/` | 不存在 |
| 业务页写成 `wiki/topic.md` | 顶层只允许三份系统页 |
| 创建 `.llmwiki/` 或 SQLite | 本 skill 不需要应用私有状态 |

## `init`

没有 `wiki/` 时必须先获得确认再创建。未确认则停止。

1. 确认 `{WIKI_ROOT}` 与研究/知识范围一句话。
2. 按下方脚手架创建骨架：`purpose.md`、`rules.md`、`raw/sources/`、`raw/assets/`、typed `wiki/` 子目录、三份系统页、`wiki/templates/`。
3. **领养已有文档**：原文件复制（或经确认后移动）到 `raw/sources/`，不要在原地改成 wiki 页。随后转 `ingest`。
4. 不要创建 `.llmwiki/`、`.obsidian/` 或任何应用私有目录。
5. 绑定工作区，追加 log：`## [YYYY-MM-DD] init | 工作区初始化`。

### 脚手架

`purpose.md`：标题「研究目标」；章节「目标」「关键问题」「范围」。用用户确认过的一句话填范围，其余可留待填写。

`rules.md` 最小内容：

```markdown
# 写作规则

- 语言跟随已有页面；空库默认简体中文。
- 事实必须能追溯到 raw 源、wiki/sources 摘要或本轮用户材料。
- 内部引用用 `[[页面标题]]`。
- 凭据与个人隐私写成 `<REDACTED>`，不入库。
- 不确定标为开放问题，不删冲突，并列保存。
```

`wiki/log.md`：

```markdown
---
title: 操作日志
---

# 操作日志

## [YYYY-MM-DD] init | 工作区初始化
```

`wiki/overview.md`：章节「项目目标」「当前状态」「主要主题」。

`wiki/index.md` 用 `lint_wiki.py --write-index` 生成，或按 typed 子目录建空表：实体 / 概念 / 源摘要 / 综合分析 / 对比分析 / 查询归档。

页面模板见 [page-types.md](page-types.md)。不要把模板复制成业务页。

### 领养已有文档

用户指向一堆已有 Markdown / PDF / 文本，且尚无上述布局时：

1. 说明将把原件收入 `raw/sources/`，wiki 页是编译产物，不是原地改名。
2. 确认复制还是移动。默认复制，保留原位置。
3. 不要把整个代码仓库当 raw 源；只收录用户指定的知识文档。
4. 骨架就绪后转 `ingest`，按文件分批，不要一次重写全部。

## `guide`

1. 读 `purpose.md`、`rules.md`、`wiki/overview.md`、`wiki/index.md`。缺哪个就说哪个，不补写。
2. 列出 `wiki/` typed 子目录页数与 `raw/sources/` 文件数（真实 `ls`，不要编目录树）。
3. 用 `rg` 或读 index 概括主题、明显缺口、错位页。
4. 总结：目标与范围、页数按类型、关键主题、下一步建议（ingest / query / organize / lint）。

## 结构描述

向用户展示目录时，引用真实 `ls` / lint 统计。不要发明占位文件名，不要画带 emoji 的假树。
