# 布局与模式

镜像根由 `detect` / `status` 给出。人读 `briefing/`，复现读 `agent/`，`evidence/` 只给路由。

默认 **briefing**。用户要可换栈复现时用 **reconstructable**。切换模式按新门禁重写内容，不是只改标题。

## 目录

```text
<spec_root>/
├── .mirror.json
├── README.md
├── changelog.md
├── briefing/
│   ├── overview.md
│   ├── architecture.md
│   ├── concepts/INDEX.md
│   ├── flows/INDEX.md
│   └── diagrams/INDEX.md
├── agent/
│   ├── INDEX.md
│   ├── specs/<capability>/spec.md
│   ├── model/INDEX.md
│   ├── surface/INDEX.md
│   └── data/INDEX.md
└── evidence/source-map.md
```

遇到旧顶层目录时见 [appendix.md](appendix.md)，不要在本文件展开迁就规则。

## `.mirror.json`

`mode`：`briefing` | `reconstructable`。`build_status`：`skeleton` | `built`。不要写 `scope` / `detail_level` / `important_paths`。

## 人读

`briefing/overview.md`：一句话、背景/目标/非目标、能力地图、主处理线。不要「待 build」/ to be built 占位交卷。

`briefing/architecture.md`：谁用、邻接、信任边界。

`briefing/flows/`：一条业务一份；步骤用业务语言。INDEX 至少一行才算有处理线。

图：复杂分叉/状态机/跨系统时序才画，见 [diagrams.md](diagrams.md)。

## Agent

`agent/INDEX.md` 只维护**一张**能力表（表头第一列是 `能力` 或 `Capability`）：

| 能力 | 一句话 | 状态 | 页 |
|------|--------|------|-----|
| checkout | 下单 | ready | [checkout](specs/checkout/spec.md) |

状态：`draft`（有 Purpose）| `ready`（每条 Requirement 至少一条 WHEN/THEN Scenario）。

未覆盖的代码入口写入同一文件的「未指定」表（表头第一列 `未指定`、`路径` 或 `Path`）：

| 路径 | 原因 |
|------|------|
| `cmd/legacy` | 一次性脚本，不进复现范围 |

`reconstructable` 下：未映射到 source-map 的代码文件必须出现在「未指定」，幽灵 source-map 行（无对应能力）不得留。

`agent/specs/<slug>/spec.md`：Purpose / Requirement / Scenario。写行为，不写当前函数步骤。

`agent/model` / `surface` / `data`：实体与不变式、对外入口与错误分类、逻辑存储与一致性。不绑语言或引擎品牌，除非那就是对外契约。

## source-map

```markdown
# 源映射

| 能力 | 源路径 | spec |
|------|--------|------|
| checkout | `internal/order` | [checkout](../agent/specs/checkout/spec.md) |
```

`route` / `finalize` 靠这张表。rename 由 CLI 回写路径。

## 完成门（finalize）

`finalize` 是唯一能把状态写成 `built` 的命令。

| 模式 | 必须 |
|------|------|
| 两者 | overview 已写（无「待 build」/ to be built）；≥1 条处理线；≥1 条能力；source-map 非空；briefing 无禁写泄漏 |
| `reconstructable` | 每条能力有 spec 且含 Requirement 与 Scenario；代码文件都被 map 或「未指定」；无幽灵 map 行 |
| `update` | 本轮 `unmapped` 已消化（并入能力或「未指定」） |

Git 源必须 `--commit`。非 Git 不得伪造 commit；`status` 会列出相对 source-map 新出现/消失的入口。

## 读者口吻

标题写项目名或主题，例如 `# <project>`。不要用「Spec 镜像」「孪生规格」「不是 OpenSpec」当开篇。
