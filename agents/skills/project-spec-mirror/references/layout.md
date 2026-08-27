# 金字塔布局与展示

镜像根是 `detect` / `status` 给出的 `spec_root`（工程内为 `spec/`，否则为 `spec/<project>/`）。所有给人读的正文都在这里。

## 目录

```text
<spec_root>/
├── .mirror.json          # 机械状态，不给人读
├── README.md             # 入口：怎么读、版本、地图
├── overview.md           # 一层：项目是什么、为什么、模块与主路径
├── changelog.md          # 镜像同步史，不是产品 changelog
├── concepts/
│   ├── INDEX.md
│   └── <concept>.md
├── entities/
│   ├── INDEX.md
│   └── <entity>.md
├── flows/
│   ├── INDEX.md
│   └── <flow>.md
└── modules/
    ├── INDEX.md
    └── <module>/
        ├── README.md     # 模块职责、文件与核心功能
        └── files/        # 仅详尽模式：每源文件一页
            └── <file>.md
```

不要额外再造顶层分类。构建产物、第三方、测试夹具默认不进 `modules/`，除非处理线必须引用。

## 阅读顺序（强制）

从上往下写，也从上往下给人看：

1. `README.md` — 30 秒：这是什么镜像、当前版本、四张地图入口
2. `overview.md` — 5 分钟：背景、目标、边界、模块图、主处理线
3. `concepts/` / `entities/` / `flows/` — 按需：词、对象、端到端
4. `modules/` — 最后：代码如何承载上面三层

下层**不得**重复上层已经说清的论点；只补充证据、接口、文件和例外。INDEX 用表格，一篇正文一个主题。

## `.mirror.json`

```json
{
  "version": 1,
  "project": "example-api",
  "placement": "in-project",
  "source": "..",
  "branch": "main",
  "mode": "concise",
  "scope": [],
  "synced_commit": null,
  "synced_at": null,
  "updated_at": "2026-01-02T00:00:00Z"
}
```

- `placement`：`in-project` | `external`
- `source`：相对本镜像根；`in-project` 时为 `..`
- `scope`：详尽模式的源路径前缀；空表示全库（仍受 inventory 忽略规则约束）
- `synced_commit`：已写入金字塔的那个 commit；未 build 则为 `null`

只通过 `init` / `set-sync` 改这个文件。

## README.md

保持短。推荐结构：

```markdown
# Spec 镜像 — <project>

给人读的孪生规格，不是源码、不是 OpenSpec。

| 项 | 值 |
|----|-----|
| 粒度 | concise |
| 分支 | main |
| 同步 commit | `abc1234`（尚未同步则写「尚未同步」） |
| 源 | git（或「非 git」） |

## 怎么读

1. [overview.md](overview.md)
2. [概念](concepts/INDEX.md) · [实体](entities/INDEX.md) · [处理线](flows/INDEX.md)
3. 需要看代码承载时再进 [模块](modules/INDEX.md)

## 地图

| 层 | 路径 | 回答什么 |
|----|------|----------|
| 总览 | overview.md | 这是什么、边界在哪 |
| 概念 | concepts/ | 领域用语 |
| 实体 | entities/ | 关键对象及其关系 |
| 处理线 | flows/ | 一次业务怎么走完 |
| 模块 | modules/ | 代码如何落地 |
```

## overview.md

用短段和列表，不用大段散文：

1. **一句话** — 这个项目做什么
2. **背景与目标** — 谁用、解决什么、非目标
3. **模块地图** — 表格：模块 / 职责 / 入口路径
4. **主处理线** — 链到 `flows/` 里最重要的 1–3 条
5. **关键实体与概念** — 链到对应页面，不在这里下定义

## 模块页

`modules/<module>/README.md`：

- 职责（相对 overview 只写本模块的）
- 对外入口（命令、HTTP、消息、库 API）
- 文件表：路径 / 一句话 / 核心符号（简约模式到此为止）
- 依赖的其他模块、实体、处理线

详尽模式的 `files/<file>.md` 见 [modes.md](modes.md)。文件路径中的 `/` 改成 `__` 作为页名，避免建深层目录，页内用源相对路径标明真身。

## changelog.md

只记录镜像同步，不抄 `git log` 全文：

```markdown
# 镜像同步

## 2026-01-02 — `abc1234`

- 模式：concise
- 范围：全库（或列出路径）
- 变更：新增 checkout 处理线；订单模块文件表更新
```

## 展示原则

- 标题即论点；表格优先于段落。
- 标识符、文件名、命令保持原文；叙述用中文。
- 每页开头用 1–3 句让人决定要不要继续读。
- 交叉链接用相对 Markdown 链接；概念 ↔ 实体 ↔ 处理线 ↔ 模块能互相跳。
- 不确定就写「未知 / 推断」，并标出来源路径；不要把命名猜测写成事实。
