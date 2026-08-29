# 工程切面

金字塔（概念 / 实体 / 处理线 / 模块）回答「这是什么」。恢复投影（`context/` `data/` `surface/` `runtime/` `build/`）回答「只凭镜像能否重建可运行系统」。切面回答「怎样可验证地改、迁、验」。三者并存，不互相替代。拓扑与启动走 `runtime/` / `build/`；本目录的 `contracts/runtime.md` 只写指标、灰度条件、回滚条件。

参考结构来自可执行契约 + 垂直切片：先把现状变成证据，再以切片为最小交付单元；**不必等全部契约写完才开始维护切片**。PHP→Go 一类双栈迁移只是对照实现的一种实例，正文用「现状实现 / 对照实现」，不要写死语言对。

## 目录

```text
<spec_root>/facets/
├── INDEX.md
├── source.md              # SOURCE 现状来源
├── contracts/
│   ├── INDEX.md
│   ├── structure.md       # 结构契约
│   ├── behavior.md        # 行为契约
│   ├── side-effects.md    # 副作用契约
│   ├── decisions.md       # 决策契约
│   └── runtime.md         # 运行契约
├── slices/
│   ├── INDEX.md
│   └── <slice>.md
├── verify.md              # VERIFY 差分 / 对照验证
└── traffic.md             # TRAFFIC 影子、灰度、切换、回滚（不适用则写「无」）
```

build / update 保留这些稳定入口并维护适用切面。没有证据的契约页写「未知」和缺口；项目确实没有该能力时写 `不适用` 与证据。不要编造 OpenAPI、迁移阶段或灰度方案。

## 五层切面

| 切面 | 页 | 回答什么 |
|------|-----|----------|
| SOURCE | `source.md` | 事实从哪来：本工程代码、配置、已有测试、脱敏请求/样本（不含三方安装树与外来仓源码） |
| CONTRACT | `contracts/` | 必须保持为真的约定 |
| SLICE | `slices/` | 一条可独立交付的垂直切口 |
| VERIFY | `verify.md` | 如何证明行为仍真（测试、性质、对照差分） |
| TRAFFIC | `traffic.md` | 如何发布与回滚（含影子 / 灰度；没有则写「无」） |

`facets/INDEX.md` 用表格链到上列五层。没有对照实现时，VERIFY 仍写现有测试、静态检查或可验证性质，差分写 `不适用`；完全没有可执行验证时写缺口。没有灰度但存在部署时，TRAFFIC 写实际发布与回滚；库、纯文档等没有部署/流量生命周期的项目可写 `不适用` 与证据。

## 契约种类

`contracts/INDEX.md` 五张表，缺哪种就空表而不是删列：

| 种类 | 页 | 典型内容 |
|------|-----|----------|
| 结构 | `structure.md` | 路由清单、OpenAPI/Schema、消息名 |
| 行为 | `behavior.md` | 特征测试、Golden Case、输入→输出 |
| 副作用 | `side-effects.md` | DB / MQ / 外部调用断言 |
| 决策 | `decisions.md` | 轻量意图、ADR、开放问题 |
| 运行 | `runtime.md` | 指标、灰度条件、回滚条件（拓扑见 `<spec_root>/runtime/`） |

契约必须能追溯到 SOURCE（路径或测试名）。解释意图用短段；固化行为优先链到测试，不要把测试抄进 Spec。

## 垂直切片

切片是工程交付单元：从入口（路由/命令/消费者）经业务与数据到外部副作用，能单独验证。处理线（`flows/`）是给人看的业务路径；一条切片通常链 1 条处理线，不要复制流程全文。

切片 ≠ 源文件。一条切片穿过多个文件；不要按文件建切片页，也不要为切片里的每个文件建 `notes/`。切片**入口**文件在模块表写不下入口协议时，可成为热点详注（见 [modes.md](modes.md)）。

**生命周期**（写在切片页顶部，按事实推进，不许跳步假装完成）：

```text
identified → characterized → specified → implemented → verified → canary → migrated → retired
```

| 状态 | 含义 |
|------|------|
| identified | 有边界和名字 |
| characterized | 已对照现状实现，有来源路径 |
| specified | 本片相关契约足够开始改 |
| implemented | 对照实现或改动已落在源码（镜像只记录，不写源码） |
| verified | 差分或测试已证明本片 |
| canary | 部分流量 |
| migrated | 流量已切走 |
| retired | 旧路径已下线 |

单实现、无灰度的项目：用到 `verified` 即可，后面标「不适用」。

切片页最少包含：一句话目标、入口、SOURCE 链接、契约链接、处理线链接、生命周期、副作用、验证方式。图放 `diagrams/`，页内只链过去。

推荐循环（有对照实现时）：选切片 → 分析现状行为 → 特征测试 → 轻量契约 → 实现对照侧 → 差分 → 灰度 → 回写本镜像。无对照实现时停在「特征测试 + 契约 + 源码同步」，VERIFY 仍记录这些测试。

## 维护

- 新增切片：源码里能划清入口与副作用时再建页；先 identified，再补契约。
- 更新：`diff` 波及的路由/schema/测试按 [routing.md](routing.md) 改对应契约与切片，overview 只在地图变了才改。
- `<!-- manual -->` 块同样不可覆盖。
- 切面与金字塔、恢复投影交叉链接：切片 → flow / module / entity / surface；契约 → 测试路径；VERIFY → `build/` 测试命令。
