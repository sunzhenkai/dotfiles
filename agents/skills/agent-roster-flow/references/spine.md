# Spine

Flow Instance 的状态。不进 git。路径：`~/.cache/agent-roster/flows/<flow_id>/`。

```text
~/.cache/agent-roster/flows/<flow_id>/
├── spine.md
└── handoffs/          # 仅 Simple plan 等没有既有 skill 路径的 Handoff
```

`<flow_id>` = `<YYYYMMDD-HHMMSS>-<slug>`。`<slug>` 用几个词概括任务。

## `spine.md`

```markdown
# <flow_id>

- **任务**: <一句话>
- **cwd**: <工作目录>
- **Track**: simple | medium | complex | unset
- **当前 Stage**: understand | plan | plan-review | implement | code-review | wrap-up
- **状态**: ongoing | done | blocked

## Assignment

| Stage | Endpoint | Model | 性质 |
|---|---|---|---|
| understand | orchestrator/<kind> | <model 或 unknown> | resident |
| plan-review | human | — | human |

## Handoff

| Stage | 路径 |
|---|---|
| plan | <path> |

## 阻塞

- <卡住了、在等什么；无则写 无>
```

- Resident 行的 Endpoint 写成 `orchestrator/<kind>`，不是名册里的可派 Endpoint。
- `human` 的 Model 列写 `—`。
- 代码评审跳过：Assignment 表不写该行，Handoff 表写 `skipped`。
- 不得把完整对话或 Run NDJSON 抄进 spine。
