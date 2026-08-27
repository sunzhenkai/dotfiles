---
id: skill-evolver
name: skill-evolver
description: "Analyze real-world Skill execution experiences, identify repeatable improvements, generate safe Skill patches, validate them against existing behavior, and evolve Skills through versioned improvements. 用户点名 skill-evolver、要求根据执行经验进化/改进已有 Skill 时使用。不要在每次任务结束后自动改 Skill。"
---

# Skill Evolver

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

你负责让已有 Skill 持续进化。

你的目标不是每次任务后都修改 Skill，而是从多次真实执行中发现**稳定、可复用、可验证的改进模式**，然后生成新的 Skill 版本。

目标 Skill 还没有 `examples/` `evals/` `experience/` 时，先走 `skill-upgrader` 做结构升级；本 skill 只负责基于真实经验改正文。

## 门禁

未过门禁不得进入本 skill 的分析、patch、晋升。

1. **仅显式触发**：用户点名本 skill / `{{slash:skill-evolver}}`，或明确要求根据执行经验进化、改进、修补已有 Skill。
2. **禁止自动进化**：普通任务完成、一次失败、一次用户纠正，都不足以自行改 Skill。
3. **先提案后动手**：未展示 Evolution Proposal 并获得用户确认前，不写候选稿，更不改生产 Skill。

**不算触发**：单独的「这个任务失败了」「帮我改一下这段」「记住这个」。用户没有要进化 Skill 时，当普通任务处理。

## Core Loop

始终遵循：

Experience
→ Analyze
→ Identify Pattern
→ Propose Improvement
→ Patch Skill
→ Evaluate
→ Promote or Reject

不要直接修改生产 Skill。

---

## 1. 收集 Experience

从以下信息中提取经验：

- Task / User Request
- Skill 使用过程
- Tool Calls
- Intermediate Decisions
- Final Result
- User Feedback
- Explicit Correction
- Failure / Retry
- Evaluation Result

重点关注：

### Failure

例如：

- 用户明确指出错误
- Tool 调用失败
- 输出需要重做
- Agent 重复尝试
- 结果与预期不一致

### Success

例如：

- 用户明确认可
- 一次完成
- 明显优于历史结果
- 某种执行路径稳定成功

### Repeated Pattern

优先关注重复出现的问题。

一次偶然失败通常不足以修改 Skill。

---

## 2. 判断是否值得进化

只有满足以下条件之一才提出 Skill 改进：

- 同类问题重复出现
- 出现明确且可复用的规则
- 可以通过 Skill instructions 避免失败
- 可以增加一个可靠的验证步骤
- 可以增加一个稳定的例子
- 可以减少明显的无效操作

不要因为一次特殊 Case 就修改 Skill。

证据不足时输出 `no-evolve`，说明缺什么，然后停止。不要硬编 Proposal。

---

## 3. 提炼 Evolution Proposal

将经验转换成明确的 Proposal：

```yaml
skill: <skill-name>

problem:
  <当前 Skill 存在的问题>

evidence:
  - <证据1>
  - <证据2>

pattern:
  <发现的稳定模式>

proposed_change:
  <建议如何修改 Skill>

expected_improvement:
  <修改后预期改善>

risk:
  low | medium | high
```

先把这份 YAML 展示给用户。用户确认后再进入 Patch。

`risk: high`（改变触发条件、删除既有硬规则、扩大权限、改脚本副作用）必须等用户明确同意；沉默不等于同意。

---

## 4. Patch Skill

生产 Skill = 当前 Agent 实际加载的那份 `SKILL.md`（及它声明要读的 `references/` / `scripts/`）。

**禁止**直接改生产稿。先在候选目录做最小 patch：

```text
<skill-dir>/evolutions/<YYYYMMDD>-<slug>/
  proposal.yaml
  SKILL.md          # 候选正文
  eval.md           # 验证记录（下一步写）
  decision.md       # promote | reject
```

规则：

1. 以生产 `SKILL.md` 为底稿复制，只改 `proposed_change` 对应的局部。
2. 一次进化只修一个稳定模式。不要顺手重构、改写无关段落、扩 scope。
3. 保留现有正确行为；新增规则要可执行（步骤、检查、例子），不要写「注意」「尽量」。
4. 过拟合禁止：不要把一次任务的路径、文件名、密钥、机器专属环境写进 Skill。
5. 正文保持精简。细节放 `references/`，确定性操作放 `scripts/`。脚本只做确定性事，不解析自然语言意图。

若目标 Skill 在本仓库：生产稿是 `agents/skills/<id>/`，**不要**改 sync 生成的 `~/.agents/skills/` 镜像。

---

## 5. Evaluate

对照**现有行为**验证候选稿，而不是只看文案是否更完整。

在 `eval.md` 记录：

- **回归**：按当前 Skill 的成功路径走一遍，确认没被新规则打断
- **模式**：原先失败/重试的那类问题，按新指令是否能避免
- **契约**：若目标 Skill 自带测试，跑它的测试；没有测试就做指令级对照，不编造分数
- **副作用**：触发范围是否被意外扩大或缩小；权限、破坏性操作、密钥处理是否变松
- **结论**：`pass` | `fail`，以及失败原因

任一项失败 → 修候选稿再评，或 `reject`。不要带着失败结果晋升。

---

## 6. Promote or Reject

| 结论 | 动作 |
|------|------|
| `promote` | 用户确认后，用候选 `SKILL.md` 覆盖生产稿；`decision.md` 写 `promote` 与原因。本仓库晋升后提醒用户跑 `scripts/agents/sync.sh` / `dotf agents -c`，**不要擅自 sync 或 commit** |
| `reject` | 不改生产稿。`decision.md` 写 `reject` 与原因。保留 `evolutions/` 作为否决记录 |

晋升前必须同时满足：

- 用户已确认 Proposal 与候选 diff
- Evaluate 为 `pass`
- 改动与 Proposal 一致，没有夹带无关编辑

拒绝同样是成功结局。不要为了「有产出」而晋升。

---

## 安全约束

- 不把密钥、内部 URL、公司代码、个人凭据写进 Skill
- 不删除仍在生效的安全/门禁规则，除非证据表明该规则本身在制造系统性失败，且用户确认
- 不把本 skill 用于从零创建新 Skill（那是写作/安装类 skill 的事）
- 一次会话最多推进 **一个** 目标 Skill 的一轮进化

## 交付

每轮结束用简短结构汇报，不要贴整份 Skill：

```text
skill: <name>
decision: no-evolve | patched | promote | reject
pattern: <一句话>
change: <一句话>
eval: pass | fail | skipped
next: <用户需要确认的事，或停止>
```
