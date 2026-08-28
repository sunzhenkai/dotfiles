# 金字塔布局与展示

镜像根是 `detect` / `status` 给出的 `spec_root`：仅当目标 source 就是当前仓时为该仓的 `spec/`，否则为 `<cwd>/spec/<project>/`。所有给人读的正文都在这里。

## 目录

```text
<spec_root>/
├── .mirror.json          # 机械状态，不给人读
├── README.md             # 入口：怎么读、版本、地图
├── overview.md           # 一层：项目是什么、为什么、模块与主路径
├── changelog.md          # 镜像同步史，不是产品 changelog
├── context/              # 恢复：系统在环境里的位置
│   └── INDEX.md
├── data/                 # 恢复：持久化与一致性
│   └── INDEX.md
├── surface/              # 恢复：对外表面
│   ├── INDEX.md
│   └── config.md         # 配置键表
├── runtime/              # 恢复：进程与部署拓扑
│   └── INDEX.md
├── build/                # 恢复：构建 / 测试 / 迁移 / 启动
│   └── INDEX.md
├── concepts/
│   ├── INDEX.md
│   └── <concept>.md
├── entities/
│   ├── INDEX.md
│   └── <entity>.md
├── flows/
│   ├── INDEX.md
│   └── <flow>.md
├── modules/
│   ├── INDEX.md
│   └── <module>/
│       ├── README.md     # 职责、根路径、文件表、核心符号
│       └── notes/        # 可选热点详注；init/build 默认不建
│           └── <source-rel>.md
├── facets/               # 工程切面：来源 / 契约 / 切片 / 验证 / 流量
│   ├── INDEX.md
│   ├── source.md
│   ├── contracts/
│   ├── slices/
│   ├── verify.md
│   └── traffic.md
└── diagrams/             # archify HTML（及同 slug 的 JSON 候选）
    └── INDEX.md
```

顶层仅限本文件列出的目录，不要再另造分类。`notes/` 挂在模块下，不是新的顶层。不要用 `files/` 为每个源文件建页。构建产物、三方安装树（`vendor/`、`node_modules/` 等）、外来仓源码、测试夹具不进 `modules/` / `notes/`。处理线或切片若用到某依赖，只写包名、接口或 `context/` 邻接，不把对方源文件列入文件表。恢复投影细则见 [projections.md](projections.md)；切面细则见 [facets.md](facets.md)；图表见 [diagrams.md](diagrams.md)；文件如何映射到页见 [routing.md](routing.md)；粒度见 [modes.md](modes.md)。

## 阅读顺序（强制）

从上往下写，也从上往下给人看：

1. `README.md` — 30 秒：这是什么镜像、当前版本、地图入口
2. `overview.md` — 5 分钟：背景、目标、边界、模块图、主处理线、主切片
3. `context/` / `surface/` / `data/` / `runtime/` / `build/` — 恢复可运行系统所需的投影
4. `facets/` — 来源、契约、垂直切片、验证与流量（工程怎么改）
5. `concepts/` / `entities/` / `flows/` — 按需：词、对象、端到端
6. `modules/` — 最后：代码如何承载（模块 README；`notes/` 仅热点）
7. `diagrams/` — 看图，不替代上文段落

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
  "hotspots": [],
  "synced_commit": null,
  "synced_at": null,
  "updated_at": "2026-01-02T00:00:00Z"
}
```

- `placement`：`in-project` | `external`
- `source`：相对本镜像根；`in-project` 时为 `..`
- `scope`：知识覆盖的源路径前缀；空表示全库（仍受 inventory 忽略规则约束）。不是「详页文件清单」
- `hotspots`：可选；已确认要写 `notes/` 的源相对路径。缺省视为 `[]`。只通过 `set-sync --hotspot` 写回；模块 README「热点」表给人读
- `synced_commit`：已写入金字塔的那个 commit；未 build 则为 `null`

只通过 `init` / `set-sync` 改这个文件。

## README.md

保持短。推荐结构：

```markdown
# Spec 镜像 — <project>

给人读的孪生规格，不是源码、不是 OpenSpec。验收：只凭本镜像能重建可运行系统。

| 项 | 值 |
|----|-----|
| 粒度 | concise |
| 分支 | main |
| 同步 commit | `abc1234`（尚未同步则写「尚未同步」） |
| 源 | git（或「非 git」） |

## 怎么读

1. [overview.md](overview.md)
2. [上下文](context/INDEX.md) · [表面](surface/INDEX.md) · [数据](data/INDEX.md) · [运行时](runtime/INDEX.md) · [构建](build/INDEX.md)
3. [切面](facets/INDEX.md) · [概念](concepts/INDEX.md) · [实体](entities/INDEX.md) · [处理线](flows/INDEX.md)
4. 需要看代码承载时再进 [模块](modules/INDEX.md)；看图进 [diagrams/INDEX.md](diagrams/INDEX.md)

## 地图

| 层 | 路径 | 回答什么 |
|----|------|----------|
| 总览 | overview.md | 这是什么、边界在哪 |
| 上下文 | context/ | 系统在环境里的位置 |
| 表面 | surface/ | 对外接口与配置键 |
| 数据 | data/ | 持久化与一致性 |
| 运行时 | runtime/ | 进程、部署、拓扑 |
| 构建 | build/ | 如何构建、迁移、启动 |
| 切面 | facets/ | 来源、契约、切片、如何验证与放量 |
| 概念 | concepts/ | 领域用语 |
| 实体 | entities/ | 关键对象及其关系 |
| 处理线 | flows/ | 一次业务怎么走完 |
| 模块 | modules/ | 代码如何落地 |
| 图 | diagrams/ | 结构 / 流程 / 时序 / 数据流 / 状态 |
```

## overview.md

用短段和列表，不用大段散文：

1. **一句话** — 这个项目做什么
2. **背景与目标** — 谁用、解决什么、非目标
3. **恢复入口** — 链到 context / surface / data / runtime / build，不在这里下定义
4. **模块地图** — 表格：模块 / 职责 / 入口路径（即模块根）
5. **主处理线** — 链到 `flows/` 里最重要的 1–3 条
6. **主切片** — 链到 `facets/slices/` 里正在维护的切口
7. **关键实体与概念** — 链到对应页面，不在这里下定义
8. **图** — 链到 `diagrams/`，没有图则省略本节

## 模块如何划

模块是连贯的代码边界，由 Agent 划分，**不是**一个源文件一模块。

| 生态 | 优先切法 |
|------|----------|
| Go | package 或 `cmd/<bin>`；多个紧密 package 可合成一个模块 |
| Python | 包目录；单文件脚本可自成模块 |
| JS/TS | `src/` 下功能目录；组件+样式+测试算该目录下的多行，不拆成三页 |
| Java | 领域包，不要一类一模块 |

单模块文件表过长（经验：> 40 行）→ 拆模块，不要改回每文件一页。

`modules/INDEX.md` 用表格：模块 / 根路径 / 一句话 / 页。

## 模块页

`modules/<module>/README.md` 固定结构：

```markdown
# <module>

<1–3 句：职责，相对 overview 不重复项目级论点>

## 根

| 路径前缀 | 角色 |
|----------|------|
| `internal/order` | 领域包 |
| `cmd/orderd` | 进程入口 |

## 对外入口

命令、HTTP、消息、库 API。

## 文件

| 文件 | 职责 | 核心 |
|------|------|------|
| `internal/order/service.go` | 下单与取消 | `Place`, `Cancel` |

## 依赖

链到实体、处理线、切片、其他模块。
```

- **根**：路由用的路径前缀，也给人看边界。每个模块至少一行。标题必须是 `根` 或 `Roots`。
- **文件**：落地证据。标题必须是 `文件` 或 `Files`。简约核心列只写名字；详尽可在表下加「核心符号」小节（不是每文件一节）。
- **热点**（可选）：仅当有 `notes/` 时增加一表：路径 / 为何 / 页。

详尽模式如何写深、何时建 `notes/`，见 [modes.md](modes.md)。`notes/` 与源树同构，页内用源相对路径标明真身。

已有镜像若含 `modules/*/files/`：视为遗留，停更、不删；在本模块 README 注明可能过期。

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
- 交叉链接用相对 Markdown 链接；概念 ↔ 实体 ↔ 处理线 ↔ 模块 ↔ 切片 ↔ 恢复投影能互相跳。
- 图只放 `diagrams/` 的 archify HTML 链接；Markdown 里不要再画一遍拓扑。
- 不确定就写「未知 / 推断」，并标出来源路径；不要把命名猜测写成事实。
