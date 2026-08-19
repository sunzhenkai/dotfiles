# Eval 抽取与 schema

## 原则

- 只从现有 `SKILL.md`（及其 references / 已有测试）抽取，不发明能力。
- 优先 `judge: deterministic`。无法用文件/命令/清单判定时才 `llm`。
- 每个 case 必须能独立判 pass/fail。
- 覆盖五类，但一类里没有依据就留空，不要凑数。

## 覆盖映射

| kind | 从原文哪里抽 |
|------|----------------|
| `basic` | 触发/门禁、最小输入输出、必读文件 |
| `core` | 主工作流步骤、交付格式、硬性 MUST |
| `failure` | 明确禁止的行为、常见误用（未点名却执行、缺输入就猜） |
| `boundary` | 作用域边界、与相邻 skill 的分工、幂等/已存在文件 |
| `regression` | 现有测试、历史事故、原文里的「不要再…」 |

## `evals/cases.yaml`

```yaml
version: 1
skill: <skill-id>
cases:
  - id: <kebab-id>
    kind: basic | core | failure | boundary | regression
    judge: deterministic | llm
    description: <一句话成功标准>
    given: <前置条件 / 输入>
    expect:
      must:
        - <必须为真的可观察事实>
      must_not:
        - <必须不发生的行为>
```

约定：

- `id` 在文件内唯一，稳定后不要改名（回归靠它）。
- `must` / `must_not` 写可观察事实（文件是否存在、是否改了生产稿、交付里是否含某字段），不写「应该更友好」。
- 本仓库目标 Skill 若已有 `tests/`，加一条 `kind: regression`、`judge: deterministic`，`must` 指向「相关测试仍通过」；不要在 yaml 里复制整份测试。

## 抽取步骤

1. 列出原文中的 MUST / 禁止 / 交付清单 / 门禁。
2. 每条变成一个 case：`given` = 触发该规则的情境，`expect` = 规则本身。
3. 门禁类同时写 `basic`（正确触发）和 `failure`（未触发却执行）。
4. 数一下 `core`：主路径至少 1 条，否则升级未完成。
5. 写完后通读 yaml，删掉无法验证或原文没有依据的条目。
