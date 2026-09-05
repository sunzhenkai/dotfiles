---
id: taskflow
name: taskflow
description: 用一个 driver change 编排一批子 change 的任务生命周期：`taskflow-new` 建 `{task}-driver`（`skip_specs: true` + 协议写进 proposal），explore / propose / apply / archive 全部委托 stock `openspec-*` skill，进度只认 OpenSpec checkbox，零脚本、无第二份任务账本。独立子 change 与独立 task 在有多 agent 时并行 apply。在用户点名 taskflow、执行 `taskflow-new`、跟进 `{task}-driver`、要把一个任务拆成多个 OpenSpec change 时使用。
---

# taskflow

面向用户默认使用简体中文；命令、路径、代码、状态值与既成术语保持原文。

一个任务 = 一个 driver change `{task}-driver`。实现拆成若干子 change `{task}-<slice>`，与 driver 同一 planning root；跨 root 时在 driver 涉及面表里显式记录 root 或 store id。共享 `{task}` 前缀让 `openspec list` 直接看出归属，不需要额外元数据。

**进度只有 checkbox 一种真相。** 不建 `tasks/` 台账、不写索引文件、不引入编号体系、不带脚本。

## 阶段路由

| 阶段 | 入口 | 参数 |
|------|------|------|
| 立项 | 本文件「脚手架」小节（command `taskflow-new`） | 任务描述 |
| 澄清 | stock skill `openspec-explore` | `{task}-driver` |
| 收敛（可选） | skill `task-grill` | `{task}-driver` |
| 提案 | stock skill `openspec-propose` | `{task}-driver` |
| 实施 | stock skill `openspec-apply-change` | `{task}-driver` |
| 归档 | stock skill `openspec-archive-change` | `{task}-driver`（只归档 driver 自身） |

taskflow 只提供 `taskflow-new` 一个 command，四个阶段一律复用 stock skill，不另造等价命令。

## 委托契约

`openspec-*` skill 默认由 `dotf agents -c` 装到全局 `~/.agents/skills`（`openspec init --tools agents`），**不是每个仓都自带**。委托前确认当前 agent 环境能读到它们；不可用就停下报告并给出可选项（跑 `dotf agents -c` / `openspec init --tools agents` 装到全局，或改用 openspec CLI 直调），**不要自行发明等价命令**。

可用时，委托必须同时具备两项绑定：**在 driver 的 planning root 下执行**，并**显式给出 change name `{task}-driver`**。缺任一项不得委托——openspec CLI 只认 cwd 最近的 `openspec/`，无绑定会写错位置或反问用户选 change。无法确定时停下报告。

## 脚手架

`taskflow-new {任务描述}` 固定三步，不多做：

1. 由任务描述归纳 kebab-case 的 `{task}`（Agent 自己归纳，不追问用户；描述确实为空时才问「要做什么？」）。
2. `openspec new change {task}-driver --goal "<任务描述原文>"`。
3. 在该 change 的 `.openspec.yaml` 补 `skip_specs: true`，再按下方模板写 `proposal.md`。

`skip_specs: true` 必须显式写入：driver 无 spec 增量，不写这行会让 `openspec validate --strict` 失败；写了之后 `openspec status --change {task}-driver --json` 中 specs 为 `skipped`。

**不要写 `tasks.md`。** 它留给 propose 阶段：stock `openspec-propose` 只处理未完成的 artifact，脚手架把 tasks 写满会让它空转，留出空缺才会读 proposal 并按协议产出登记了子 change 的 `tasks.md`。这也是协议必须写在 proposal 而不是别处的原因——`openspec instructions apply --json` 的 `contextFiles` 保证 proposal 必然被读到。

### driver `proposal.md` 模板

`Driver 协议` 小节是固定文本，逐字写入，不要改写或精简；其余小节按任务填写。

````markdown
## Why
<任务描述>

## What Changes
- 本 change 是 taskflow driver，不直接改代码，只编排子 change

## Non-goals
- <...>

## 涉及面
| 仓库 | 角色 | 说明 |
|------|------|------|
| . | 必须 | 会修改，实施前切任务分支 |

## 验收标准
- [ ] <...>

## Driver 协议
- 本 change 无 spec 增量（`.openspec.yaml` 已设 `skip_specs: true`）
- 子 change 一律命名 `{task}-<slice>`，与本 change 同一 planning root；跨 root 时在涉及面表显式记录 root 或 store id
- 实现进度只认子 change 自己的 `tasks.md`；本文件的 checkbox 只在对应子 change 全勾且 `validate --strict` 通过后才勾
- 涉及面里角色为 `必须` 的仓在实施前切任务分支：没有则 `git switch -c`，已有则 `git switch`。不许 stash / reset / 强制切换。工作树 dirty 时：未提交路径仅含当前 task 的 OpenSpec change（`openspec/changes/{task}-*`）则直接切；否则列出路径并确认是否继续 checkout。用户不同意、git 拒绝或切错仓时停下
- 只有「checkbox 全勾」「需要用户决策」「本轮预算耗尽」三种情况允许结束一轮；单项做不了就保持未勾，在验证记录写一行原因后继续下一项
- 结束时逐条列出未勾项与原因，不按 change 汇总

## 验证记录
````

### 脚手架输出

报告 change name、`proposal.md` 路径、涉及面与验收标准里仍需用户确认的空缺，并桥接到 stock `openspec-propose`（方案未定时先 `openspec-explore`）。

同时提示：driver 已存在 proposal，`openspec-propose` 会问「继续已有 change 还是新建」，**应选继续**。

## propose 阶段的产出约定

`openspec-propose` 对 driver 产出的 `tasks.md` 按下列骨架组织：准备段切分支，实施段每个子 change 至少一条，收尾段含回归、回填验收、提交与逐个子 change 的归档条目。

子 change 的 artifacts 在 propose 阶段一次性备齐（拆分粒度本身是提案决策），apply 阶段只做实施，不在实施循环里改 change 语义。

````markdown
## 1. 准备
- [ ] 1.1 把涉及面里角色为必须的仓切到任务分支

## 2. 实施
- [ ] 2.1 完成子 change `{task}-api`：apply 至全部 checkbox 勾选且 validate --strict 通过
- [ ] 2.2 完成子 change `{task}-ui`：同上

## 3. 收尾
- [ ] 3.1 全仓回归与静态检查，命令与结果写入 proposal 验证记录
- [ ] 3.2 回填 proposal 验收标准
- [ ] 3.3 提交交付仓改动
- [ ] 3.4 归档全部子 change
````

子 change 的归档是收尾段的普通 checkbox，在 apply 阶段完成。因此 driver 全勾时子 change 已全部 `openspec archive`，对 driver 执行 stock 归档不需要任何递归处理。

## 纪律

### 进度归属

- 子 change 的 `tasks.md` 记**实现**进度，driver 的 `tasks.md` 记**编排**进度，后者必然滞后于前者。
- driver 的某条实施 checkbox 只在对应子 change 全部 checkbox 已勾、且在其 planning root 下 `openspec validate --strict --type change {task}-<slice>` 通过之后才允许勾选。
- 不持久化第二份完成度、暂缓或分支状态记录。暂缓原因写进 driver `proposal.md` 的验证记录小节。
- 已知代价：`openspec archive` 对未勾 checkbox 不设防。完成度靠上述纪律与 stock skill 的确认环节，taskflow 不补脚本。

### 涉及面与交付分支

- 角色只有三个取值：`必须`（会修改，实施前切任务分支）、`建议`（只读参考）、`排除`。
- 分支准备是 driver `tasks.md` 里的 checkbox，只处理 `必须` 仓；`建议` 与 `排除` 仓保持只读。
- fail closed：**禁止**自动 stash、reset 或强制切换。目标分支不存在则 `git switch -c`，已存在则 `git switch`。工作树 dirty 时先看未提交路径：全部落在 `openspec/changes/{task}-*`（当前 task 的 driver 与子 change）则直接 checkout，不提问；否则列出路径，只确认是否继续 checkout（改动随普通 switch 带到目标分支）。不要展开成提交、留在当前分支或其它处理方式的选项。用户未确认、git 拒绝或切到非必须仓时停下。已准备成功的仓保留现状以便重试。

### 一轮结束

只有三种情况允许结束一轮：**checkbox 全勾**、**需要用户决策**、**本轮预算耗尽**。

单项做不了（依赖、环境或授权）就保持未勾，在验证记录写一行原因，继续处理不依赖它的其余条目——不要因为一项卡住就整轮停下，也不要把未完成项勾成完成。结束时逐条列出未勾条目与原因，不用「某 change 还剩 3 项」这类按 change 汇总的数量代替逐条说明。

### 并行执行

有多 agent / 子代理能力时，对**无未完成依赖、范围不重叠**的单位优先并行；没有该能力则主会话串行，其余纪律不变。并行只改变执行方式，完成度仍只认 checkbox，不另建账本。

两层都可以并行：

| 层 | 单位 | 可以并行 | 必须串行 |
|----|------|----------|----------|
| change | 子 change `{task}-<slice>` | 落在不同必须仓，或主会话已确认实现范围不重叠 | 同一工作树且可能改同一批文件或互相依赖契约；准备段切分支；收尾段回归 / 回填 / 提交 / 归档 |
| task | 同一 change 的 checkbox | 互不依赖且文件范围不重叠 | 有先后依赖、共享同一文件、或需要用户决策 |

每个子代理只领一个单位（一个子 change，或同一 change 内一组已声明不重叠的 checkbox），并同时满足：

- 在该单位的 planning root 下执行，且显式给出 change name
- 只改自己范围内的代码与自己的 `tasks.md` checkbox
- 不勾 driver 编排项（仍由主会话在子 change 全勾且 `validate --strict` 通过后勾）
- 不发明等价命令，不扩大到 `建议` / `排除` 仓的写入

主会话负责派发、汇总、处理冲突与未勾原因。子代理失败或超时不是整轮结束理由，按「一轮结束」继续其余独立项。

---

## Self-evolution

本 Skill 具备经验积累、评估与持续进化能力。目录（均相对本 Skill 根目录）：

```text
agents/skills/taskflow/
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
2. 若当前环境有 `skill-evolver`，委托它走候选 patch → 验证 → 晋升，不要本 Skill 自己改生产稿。
3. 未展示 Proposal 并获得用户确认前，不改生产 Skill。
