# 设计文档骨架

Phase 2 脚手架。按问题裁剪，不是每节都必填。

当前只写入 `<taskRoot>/design/`；`归档落点` 等到 `task-archive` 再晋升。

---

# <Title>

> 一段话：做什么、为什么、选哪条路。

## Context

- **Problem**: [要补的缺口]
- **Stakeholders**: [谁关心、谁能卡住、谁受益]
- **Success criteria**: [怎样算做成]
- **Constraints**: [技术、业务、时间、团队、合规]
- **Out of scope**: [本设计明确不做的]

## Current State

现状简述。链到已有文档、ADR、代码路径。标出必须契合的既有模式。

## Options Considered

| Option | Cost | Risk | Reversibility | Time | Complexity |
|--------|------|------|---------------|------|------------|
| A      |      |      |               |      |            |
| B      |      |      |               |      |            |
| C      |      |      |               |      |            |

每个选项 1–3 行说明。

## Recommended Approach

**Recommendation: Option X**，因为 [主因]。

接受的取舍：

- [trade-off 1]
- [trade-off 2]

回退计划：[选错了怎么撤]。

## Architecture

```
┌──────────────────────────────────────────────┐
│     ASCII or Mermaid diagram of the system   │
└──────────────────────────────────────────────┘
```

- **Component A**: [职责]
- **Component B**: [职责]
- **Data flow**: [请求 / 事件 / 状态传播]

## Interfaces

### API / message contracts

```
<Type or schema sketch>
```

### Key types

```pseudo
struct Foo { ... }
```

## State Management

- Where state lives: [DB / cache / in-memory / external]
- State transitions: [如有状态机]
- Consistency model: [strong / eventual / read-your-writes]

## Failure Modes

| Failure | Likelihood | Impact | Mitigation |
|---------|------------|--------|------------|
| [scenario] | low/med/high | [blast radius] | [handling] |

## Rollout / Migration

若改动已有系统：

- Phase 1: [shadow / dark launch / feature flag]
- Phase 2: [gradual rollout]
- Phase 3: [full migration + cleanup]

## Open Questions

- [ ] [仍未决]
- [ ] [需要的 spike]

## 归档落点（先记账，archive 时再写过去）

| 文档角色 | 类型 | 目标仓 | 计划路径 |
|----------|------|--------|----------|
| 主设计 | design | `.` 或子仓路径 | `docs/design/<domain>/<topic>.md` |
| 决策（如有） | adr | 同上 | 项目 ADR 约定（如 `docs/adr/YYYY-MM-DD-<slug>.md`） |
| 知识条目（如有） | knowledge | 同上 | concept / service / relation / pitfall |

**现在不要写入上表路径。** 本文档当前位于 `tasks/.../design/<file>.md`。

## Cross-References

- **Related designs**: [兄弟文档]
- **Downstream**: [本设计解锁的实现工作，通常是 task-propose]
