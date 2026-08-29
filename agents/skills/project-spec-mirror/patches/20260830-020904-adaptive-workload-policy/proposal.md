# 将固定工作量改为自适应策略

- target: agents/skills/project-spec-mirror
- patch: 20260830-020904-adaptive-workload-policy
- risk: high
- status: proposed

## Intent

放宽与安全、状态和机械路由无关的绝对约束，让镜像工作量随项目类型和用户目标调整：

- 每次只保持一个 active target，但允许用户要求批量项目时顺序处理，不再强制另开会话。
- 恢复投影与工程切面保留固定骨架；只深入适用能力，不适用项写带证据的 `不适用`，不制造无意义内容。
- 图表改为需求驱动：用户明确要求时必须交付；Agent 主动建议的图先评估价值和成本，不再因“识别出候选”自动阻塞整个 build。
- 文件表继续是默认阅读单位；用户明确接受成本后，可对选定范围批量建立 `notes/`，15 个改为建议批次而不是不可突破的硬上限。
- 核心顶层目录保持稳定；领域特有附加内容统一放 `extensions/<name>/`，仅在用户明确需要且现有层无法表达时使用。
- “强制阅读顺序”和模块 40 行阈值改为推荐导航与拆分信号。

非目标：不放宽密钥、外来仓、覆盖目录、确认门、状态写入、manual 块和路由表标题等安全或机械不变量。

## Conflict check

- 现有 `diagrams.md` 与 contract/eval 强制“识别即本轮交付”；改为用户请求强制、Agent 候选按价值决策。
- 现有 projections/facets 对所有项目要求完整内容；改为骨架完整、能力适用性自适应。
- 现有 layout 禁止任何顶层扩展；新增唯一受控扩展槽 `extensions/`。
- 现有 modes 对超过 15 个 notes 绝对禁止；改为默认分批，用户确认明确范围后允许。
- 不改变 `specctl validate` 所需核心文件，因此不影响既有状态和机械验证。

## Rationale

库、CLI、静态站点、服务和数据管道的运行能力不同。固定要求所有页面同样深入会产生大量“无/未知”模板和无价值图表，增加 token、时间与维护成本。保留核心骨架和硬安全边界，同时按能力和用户目标分配深度，更符合 skill-creator 的“解释 why、避免压迫性 MUST、按任务脆弱度设置自由度”原则。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 更新 active target、投影/切面、图表和文件详注策略。
- `agents/skills/project-spec-mirror/references/layout.md` — 推荐阅读顺序、受控 extensions 与模块拆分信号。
- `agents/skills/project-spec-mirror/references/projections.md` — 增加能力适用性规则。
- `agents/skills/project-spec-mirror/references/facets.md` — 允许不适用切面使用带证据的简短状态。
- `agents/skills/project-spec-mirror/references/diagrams.md` — 改为需求驱动交付。
- `agents/skills/project-spec-mirror/references/modes.md` — notes 数量改为软预算和确认批次。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 更新自适应策略验收。
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 验证图表需求驱动与硬安全边界保留。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- 检查“用户明确要求图表”仍是硬交付，“Agent 仅识别候选”不再阻塞。
- 检查密钥、外来仓、状态、覆盖和 manual 块门禁未被放宽。
