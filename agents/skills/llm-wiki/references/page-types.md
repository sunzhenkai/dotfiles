# 页面类型

业务页路径由 `type` 决定。文件名用标题的短 slug（可含中文），扩展名 `.md`。

| type | 目录 | 用途 | 必需章节 |
|------|------|------|----------|
| entity | `wiki/entities/` | 可唯一指认的对象：人、组织、产品、项目 | 概述、关键事实、相关概念、来源 |
| concept | `wiki/concepts/` | 可复用的术语、方法、框架、机制、理论 | 定义、核心要点、相关实体、来源 |
| source | `wiki/sources/` | 一份 raw 源的摘要，不是原件 | 摘要、关键观点、相关实体/概念 |
| synthesis | `wiki/synthesis/` | 跨源分析 | 问题/目的、分析、引用、后续 |
| comparison | `wiki/comparisons/` | 对比 | 对比维度、异同、结论 |
| query | `wiki/queries/` | 值得留下的问答 | 问题、回答、引用 |

关系（某实体采用某概念）用正文和 `[[wikilink]]` 表达，不要做成第三种页面类型，也不要把双方名字拼进概念标题。

## Frontmatter

业务页：

```yaml
---
title: 页面标题
type: entity
date: YYYY-MM-DD
tags: []
sources: []
related: []
---
```

- 更新时不要轻易改 `type`、`title`、`created`（若已有）。
- `tags` / `sources` / `related` 做并集去重，不覆盖删除旧值。
- `date` 用本次写入日；`created` 只在首次创建时加。
- `sources` 指向 `wiki/sources/` 页标题或 raw 文件名，便于追溯。

系统页可不设业务 `type`。模板页只存在于 `wiki/templates/`。

## 实体 vs 概念

写页前问三句：

1. 这是可指认的具体对象，还是可复用的抽象？
2. 标题是否嵌了已有实体名？
3. 若两者同时出现，是否应拆成两页再用 wikilink 连起来？

**默认**：概念标题保持中性，不把实体名嵌进去。

| 不要 | 要 |
|------|------|
| 概念页 `青禾实验室渐进披露` | 实体 `青禾实验室` + 概念 `渐进披露`，正文互链 |
| 把某组织的工具栈写成概念标题 | 中性概念 + 实体页记录其采用情况 |
| 关系页 `Foo 采用 Bar` | 在 Foo / Bar 正文中写关系 |

**例外**：来源把整句当作专有名词。保留组合标题，并在正文写明命名依据与出处。

虚构示例：实体 `青禾实验室` 是具体组织；概念 `渐进披露` 是可被多个实体引用的方法。

## 模板（init 时写入 `wiki/templates/`）

创建业务页时按对应模板补齐章节，不要把「（待填写）」留在成品里。

### entity

```markdown
---
title: 示例实体
type: entity
date: YYYY-MM-DD
tags: []
---

# 概述

## 关键事实

-

## 相关概念

- [[相关概念]]

## 来源

- [[来源页面]]
```

### concept

```markdown
---
title: 示例概念
type: concept
date: YYYY-MM-DD
tags: []
---

# 定义

## 核心要点

-

## 相关实体

- [[相关实体]]

## 来源

- [[来源页面]]
```

### source

```markdown
---
title: 示例来源
type: source
date: YYYY-MM-DD
tags: []
---

# 摘要

## 关键观点

-

## 相关实体/概念

- [[相关页面]]
```

### synthesis / comparison / query

- synthesis：问题/目的、分析、引用、后续
- comparison：对比维度、异同、结论
- query：问题、回答、引用

## 链接

- 内部用 `[[标题]]` 或 `[[entities/slug|标题]]`。
- 写 A 提到 B 时，尽量在 B 补反向链接（至少从 overview / 相关实体或概念链入）。
- 不要用纯文本名字代替已有 wiki 页。
