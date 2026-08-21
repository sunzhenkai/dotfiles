---

## Self-evolution

本 Skill 具备经验积累、评估与持续进化能力。目录（均相对本 Skill 根目录）：

```text
<skill-dir>/
├── SKILL.md
├── examples/      # 经过验证的优秀执行案例
├── evals/         # 可验证成功标准
└── experience/    # 真实失败 / 成功 / 规律
```

不要为了自进化而破坏上文已规定的目标、流程、工具用法、输出与约束。

### Examples

执行复杂任务前：

1. 检查 `examples/`
2. 找到与当前任务相关的成功案例
3. 优先复用已经验证的方法

没有相关案例时按上文正常执行，不要编造案例。

### Evaluation

任务完成前：

1. 检查相关 `evals/`
2. 验证关键输出
3. 检查是否违反 Skill 约束
4. 尽可能运行相关 Eval Cases（见 `evals/cases.yaml`）

优先确定性 Eval；无法确定性判断时再用 LLM Judge。Eval 失败则先修输出，不要带着失败交卷。

### Experience

任务完成后，出现以下情况才写入 `experience/`：

- 失败
- 用户纠正
- 明显成功
- 新的有效执行方法
- 可复用的经验

不要记录 trivial information。不要伪造条目。密钥、内部 URL、凭据不得写入。

单次失败 → `experience/failures/`。重复出现的规律 → `experience/patterns/`（至少两次同类证据）。

### Evolution

只有当 Experience 暴露出**可复用、稳定的问题或模式**时，才考虑修改本 Skill。

遵循：

```text
Experience
    ↓
Repeated Pattern
    ↓
Improvement Proposal
    ↓
Eval
    ↓
Pass
    ↓
Update Skill
```

禁止：

```text
Single Failure
    ↓
Directly modify SKILL.md
```

进入 Skill 正文的 Experience 必须同时满足：可复用于多个类似任务、有足够证据、能明确改善结果、不破坏已有能力、可通过 Eval 验证。一次性特殊情况只留 Experience，不改 Skill。

实际更新生产 `SKILL.md` 时：

1. 不要直接覆盖原文；记录 version / change / reason / evidence / evaluation。有 Git 则优先靠 Git diff 留历史。
2. 若改动来自**真实执行经验**：优先委托 `skill-evolver`（`evolutions/` → 验证 → 晋升），不要本 Skill 自己改生产稿。
3. 若只是结构/规则的显式修订且环境有 `skill-upgrader`：走其 `update` 模式（`<skill-dir>/patches/`），仍须先提案再应用。
4. 未展示 Proposal 并获得用户确认前，不改生产 Skill。
