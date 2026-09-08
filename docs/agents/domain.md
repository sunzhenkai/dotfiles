# Domain Docs

工程类 skill 在探索本仓库代码时，应按以下规则消费领域文档。

## 探索前先读这些

- 仓库根目录的 **`CONTEXT.md`**，或
- 若根目录存在 **`CONTEXT-MAP.md`**：它指向每个 context 各自的 `CONTEXT.md`。只读与当前主题相关的那些。
- **`docs/adr/`**：阅读与即将动手区域相关的 ADR。在 multi-context 仓库中，也检查 `src/<context>/docs/adr/` 下的 context 级决策。

若上述文件不存在，**静默继续**。不要标缺、不要建议先创建。`/domain-modeling` skill（经 `/grill-with-docs` 与 `/improve-codebase-architecture` 进入）会在术语或决策真正落地时再惰性创建它们。

## 文件结构

Single-context 仓库（大多数仓库）：

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context 仓库（根目录存在 `CONTEXT-MAP.md`）：

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← 系统级决策
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context 级决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用术语表里的用词

输出中命名领域概念时（issue 标题、重构提案、假设、测试名），使用 `CONTEXT.md` 中定义的术语。不要滑向术语表明确避免的同义词。

若所需概念还不在术语表里，这是信号：要么你在发明项目不用的说法（应重新考虑），要么存在真实缺口（记下，留给 `/domain-modeling`）。

## 标出与 ADR 的冲突

若输出与已有 ADR 矛盾，显式点出，不要悄悄覆盖：

> _与 ADR-0007（event-sourced orders）矛盾，但值得重开，因为……_
