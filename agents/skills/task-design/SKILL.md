---
id: task-design
name: task-design
description: 复杂任务的可选全面设计环节（在 task-explore 之后）。把决策级设计文档写到该 task 的 design/ 目录，不写实现代码；归档时再晋升到 docs/design、ADR、knowledge。在用户要全面设计、RFC、ADR、架构权衡，或 explore 后仍有多方案/跨模块契约时使用。简单、路径已清的任务不要用（直接 task-propose）。
---

# 任务设计

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

`task-*` 链路上的**可选**设计环节。Gate、status、归档晋升以 `task-workflow` 为准；本 skill 只规定**怎么写设计**。

```
task-new → task-explore? → task-design? → task-propose → task-apply → task-archive
```

## 何时使用

- 新子系统 / 服务 / 跨模块契约
- 需要在 ≥2 个可行方案里做决策（RFC、技术选型、重构边界）
- 用户明确要全面设计、架构文档、ADR
- `task-explore` 之后问题已清、但实现路径仍有架构分叉

## 何时不用

| 情况 | 改用 |
|------|------|
| 尚无 task | `task-new` |
| 问题本身还没想清 | `task-explore` |
| 范围局部、路径唯一、无架构决策 | 直接 `task-propose` |
| 要写 OpenSpec `proposal.md` / `tasks.md` | `task-propose` |
| 已经在写代码 | `task-apply` |

无已解析 task 时 **MUST** 先走 `task-workflow` 的 resolve；禁止把设计写到 `docs/design/` 或仓库根。

## MUST 先做

1. 读并执行 skill `task-workflow` 的 **task-design 职责**（resolve、Checkout Gate、路径、status）
2. 再按下面三阶段写设计

## 三阶段：探索 → 设计 → 暂存

停在实现边界。本环节**只写入** `<taskRoot>/design/`。

### 1. 探索（对话，可不落盘）

- 干系人与成功标准
- 现状：读代码与已有文档，识别既有模式
- 约束：技术 / 业务 / 时间 / 合规
- 未知与风险（明确写出「还不知道 X」）

问题仍模糊时，给出 2–3 种问题框架让用户选。

### 2. 设计

至少给出 **两个可行方案** 再推荐。

- 选项 + 对比表（成本、风险、复杂度、可逆性、工期）
- 推荐路径与取舍
- 产物见 `references/design-template.md`：架构图、职责、数据流、接口契约、状态、失败模式、迁移、未决问题

多用 ASCII / Mermaid。一张图胜过一段话。

### 3. 暂存（写入 task，不晋升）

写入 `<taskRoot>/design/`：

| 文件 | 作用 |
|------|------|
| `design/README.md` | 文档索引 + **归档落点表**（计划路径，此时还不写过去） |
| `design/<topic>.md` | 主设计（可多篇） |
| `design/adr-<slug>.md` | 若有独立决策，仍先放这里 |

归档落点表示例：

```
| 文档 | 类型 | 目标仓 | 归档落点 |
|------|------|--------|----------|
| `design/auth.md` | design | `.` | `docs/design/auth/session.md` |
| `design/adr-token.md` | adr | `.` | `docs/adr/YYYY-MM-DD-token.md` |
```

`<domain>` 跟项目子系统划分；跨切面用 `docs/design/_cross/` 或 `_shared/`，不要堆在 `docs/design/` 根下。

**禁止**在本阶段写入 `docs/design/`、ADR 目录、knowledge。晋升发生在 `task-archive`。

## 边界

- 不写实现代码
- 不创建 OpenSpec `tasks.md`
- 不把设计写到 task 目录以外
- 必须有图和权衡表
- 推荐与未决问题分开写
- 遵守目标仓文档约定（kebab-case、一篇一个 H1）

## 模板

### 对比表

```
| 方案 | 成本 | 风险 | 可逆性 | 工期 | 复杂度 |
|------|------|------|--------|------|--------|
| A    | $$   | 低   | 高     | 2w   | 低     |
| B    | $    | 中   | 低     | 1w   | 高     |
```

### 推荐

```
**推荐：方案 B**，因为 [主因]。
接受的取舍：[列表]。
回退计划：[如何撤回]。
```

### 交接（本阶段结束时）

```
## 交接

**已设计**：[一句话]
**暂存位置**：`tasks/.../TNNNN-<slug>/design/`
**归档落点**（尚未写入）:
- `docs/design/...` — [用途]
**下一步**：{{slash:task-propose}} TNNNN
**未决问题**：[列表，或无]
```

## 相关

- `task-workflow` — Gate / status / 归档晋升
- `task-explore` — 前置；想不清问题时用
- `task-propose` — 下游；把设计收成 OpenSpec change
- `references/design-template.md` — 设计文档骨架
