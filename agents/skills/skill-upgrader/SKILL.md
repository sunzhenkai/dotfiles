---
id: skill-upgrader
name: skill-upgrader
description: "Upgrade an existing SKILL.md into a self-evolving skill with examples, evals, and experience tracking. 用户点名 skill-upgrader、要求把已有 Skill 升级为自进化（加 examples/evals/experience）时使用。不要在从零写 Skill、或用 skill-evolver 进化正文时自动套用。"
---

# Skill Upgrader

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

将一个普通 Skill 升级为具备**经验积累、评估和持续进化能力**的 Skill。

最终目标：把一个静态 `SKILL.md` 升级成一个能够从真实执行中积累经验，并通过 Eval 驱动持续改进的 Skill。

## 与 skill-evolver 的关系

| Skill | 职责 |
|-------|------|
| **本 skill** | 一次性结构升级：给已有 Skill 加上 `examples/` `evals/` `experience/`，并写入自进化指令 |
| `skill-evolver` | 基于多次真实执行：提案 → 候选 patch → eval → 晋升生产稿 |

本 skill **不**根据经验改目标 Skill 的核心行为。那是 `skill-evolver` 的事。目标 Skill 尚未具备自进化目录时，先走本 skill。

## 门禁

未过门禁不得改目标 Skill。

1. **仅显式触发**：用户点名本 skill / `{{slash:skill-upgrader}}`，或明确要求把已有 Skill 升级为自进化（加 examples / evals / experience）。
2. **必须有目标**：给出 skill 名、id 或含 `SKILL.md` 的目录。未指定先问，不猜。
3. **禁止从零创建**：没有现成 `SKILL.md` 就停止。
4. **禁止伪造历史**：没有真实成功案例就不要编 examples；没有真实执行就不要写 experience 条目。

**不算触发**：从零写 Skill、安装 Skill、根据一次失败改 Skill 正文。分别走写作/安装类 skill 或 `skill-evolver`。

## Input

输入一个已有 Skill：

```text
my-skill/
└── SKILL.md
```

生产稿定位：

- 本仓库：`agents/skills/<id>/`。**不要**改 sync 生成的 `.claude/skills/`、`.cursor/skills/`、`~/.claude/skills/` 等镜像。
- 其它仓库 / 个人 skill：以含 `SKILL.md` 的目录为准。

## Output

将其升级为：

```text
my-skill/
├── SKILL.md
├── examples/
├── evals/
└── experience/
```

目录模板、Eval schema、注入正文见（均只读一层）：

- [layout.md](references/layout.md) — 复制清单
- [evals.md](references/evals.md) — 抽取规则与 schema
- [skill-injection.md](references/skill-injection.md) — 追加到目标 SKILL.md 的原文
- [examples-README.md](references/examples-README.md) / [evals-README.md](references/evals-README.md) / [experience-README.md](references/experience-README.md) / [cases.template.yaml](references/cases.template.yaml) — 复制源

---

## 工作流

复制并勾选：

```text
Upgrade Progress:
- [ ] 定位并完整读取现有 SKILL.md
- [ ] 幂等检查（已有目录/段落不覆盖）
- [ ] 创建 examples/
- [ ] 创建 evals/
- [ ] 创建 experience/
- [ ] 升级 SKILL.md（追加，不破坏原行为）
- [ ] Final Validation
```

### 1. Preserve the original Skill

首先完整读取现有 `SKILL.md`（及其声明要读的 `references/` / `scripts/`）。

保留其：

- 核心目标
- 工作流程
- 工具使用方式
- 输出要求
- 约束
- 已有最佳实践

不要为了增加自进化能力而破坏原有行为。不要重写无关段落、不要扩 scope、不要「顺手润色」。

幂等：若 `examples/` `evals/` `experience/` 已存在，保留已有文件；只补缺失的 README / 空目录 / 注入段落。已有 `evals/cases.yaml` 不覆盖，只追加从原文抽出且尚未覆盖的 case。

### 2. Create examples/

创建：

```text
examples/
└── README.md
```

用于保存经过验证的优秀执行案例。

案例应该包含：

- Task
- Approach
- Result
- Why it was good
- Reusable lessons

如果当前没有真实成功案例，不要编造案例。只建 README 与目录约定（见 [layout.md](references/layout.md)）。

### 3. Create evals/

创建：

```text
evals/
├── README.md
└── cases.yaml
```

从现有 Skill 中提取可验证的成功标准，建立 Eval Cases。覆盖：

- 基础能力
- 核心能力
- 常见失败
- 边界情况
- Regression Cases

优先使用确定性 Eval。无法确定性判断时，再使用 LLM Judge。

不要发明 Skill 里没有依据的 case。抽取方法与 schema 见 [evals.md](references/evals.md)。

### 4. Create experience/

创建：

```text
experience/
├── README.md
├── failures/
├── successes/
└── patterns/
```

用途：

```text
failures/  → 失败案例
successes/ → 成功案例
patterns/  → 从多个案例中提炼出的可复用规律
```

空目录放 `.gitkeep`。不要伪造历史 Experience。

### 5. Upgrade SKILL.md

在原 Skill **末尾追加**自进化能力，不要覆盖原内容。注入正文必须与 [skill-injection.md](references/skill-injection.md) 一致（只把 `<skill-dir>` 换成实际目录）。不要改写语气或删减门禁。若原文已有同等「Self-evolution」段落，不要再贴一份，只补缺失子节。

追加内容覆盖：

#### Examples

执行复杂任务前：

1. 检查 `examples/`
2. 找到与当前任务相关的成功案例
3. 优先复用已经验证的方法

#### Evaluation

任务完成前：

1. 检查相关 `evals/`
2. 验证关键输出
3. 检查是否违反 Skill 约束
4. 尽可能运行相关 Eval Cases

#### Experience

任务完成后，如果出现以下情况，记录 Experience：

- 失败
- 用户纠正
- 明显成功
- 新的有效执行方法
- 可复用的经验

不要记录 trivial information。

#### Evolution

只有当 Experience 暴露出**可复用、稳定的问题或模式**时，才考虑修改 Skill。

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

实际改生产 `SKILL.md` 时：若环境里有 `skill-evolver`，**委托它**（候选目录 → 验证 → 晋升），不要让目标 Skill 自己直接覆盖生产稿。

---

## Evolution Criteria

一个 Experience 只有满足以下条件才应该进入 Skill：

- 可以复用于多个类似任务
- 有足够证据支持
- 能明确改善执行结果
- 不会破坏已有能力
- 可以通过 Eval 验证

如果只是一次性特殊情况：

```text
Experience only
```

不要修改 Skill。

---

## Versioning

修改 Skill 时不要直接覆盖原内容。

记录：

```text
version
change
reason
evidence
evaluation
```

如果项目使用 Git，优先通过 Git diff 保留变更历史。本 skill 的升级本身就是一次追加：不要改写原段落来「腾地方」。

若目标 Skill 在本仓库：升级后提醒用户跑 `scripts/agents/sync.sh` / `dotf agents -c`，**不要擅自 sync 或 commit**。

## 安全约束

- 不把密钥、内部 URL、公司代码、个人凭据写进 examples / evals / experience / SKILL.md
- 不删除仍在生效的安全/门禁规则
- 一次会话最多升级 **一个** 目标 Skill
- `evals/cases.yaml` 只写可验证的期望，不写攻击步骤、exploit、凭据

## Final Validation

升级完成后确认：

```text
[ ] 原始 Skill 能力未丢失
[ ] examples/ 已建立
[ ] evals/ 已建立
[ ] experience/ 已建立
[ ] Eval 能覆盖核心能力
[ ] 没有伪造历史经验
[ ] Skill 知道如何读取 examples
[ ] Skill 知道如何运行/参考 evals
[ ] Skill 知道什么时候记录 experience
[ ] Skill 不会因为单次失败修改自己
```

任一项未完成则补齐后再交付，不要声称已升级。

## 交付

用简短结构汇报，不要贴整份 Skill：

```text
skill: <name>
path: <skill-dir>
decision: upgraded | already-upgraded | aborted
added: examples | evals | experience | skill-injection
eval_cases: <N> deterministic / <M> llm
next: <sync 提醒，或停止原因>
```
