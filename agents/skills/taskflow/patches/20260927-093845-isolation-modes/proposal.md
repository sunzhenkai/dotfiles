# 实现者隔离拆分正常交付与盲测复跑

- target: agents/skills/taskflow
- mode: update
- patch: 20260927-093845-isolation-modes
- risk: high
- status: proposed

## Intent

上一轮把「实现者不接收质量画像与 rubric」泛化成所有实现派发，这与既有规则冲突：taskflow 又要求质量画像原文进入 driver proposal 并指导实现与验收。正常交付若隐藏并发、无障碍、错误边界、运行假设，实现者无法满足要求，会造成质量倒退。

本 patch 把隔离限定为「盲测 / 基准复跑」：

1. **正常交付**：实现者必须收到质量画像、本人负责范围的相关验收要求与运行约束；完整评分 rubric 与跨范围审阅意见仍由审阅者持有。
2. **盲测 / 基准复跑**：仅当任务明确标记为 benchmark / regression 复跑时，实现者只收样例或需求原文与运行约束，不收画像、rubric、期望清单或历史审阅意见；复跑使用同一份原文，不追加事后提示。

要改变的行为：

- `implementer-isolation.md` 从全量隔离改为双模式。
- `SKILL.md` 的「实现者隔离」明确默认是正常交付；盲测必须显式标记，不得普通任务默认盲派。
- eval 拆分正常交付上下文与盲测隔离，避免旧 case 继续要求所有实现者都不见画像。
- `taskflow-orchestration` spec 同步双模式语义。

非目标：不改质量画像传递、降级确认、三层回归、rubric 通过线、Driver 协议固定文本与 checkbox 唯一真相；不让盲测模式绕过画像验收。

## Conflict check

- 与「质量画像进入 proposal 与验收」不再冲突：正常交付显式给实现者画像与相关验收要求。
- 与「实现者自评不算通过线」不冲突：完整 rubric 与最终评分仍归审阅者。
- 与 checkbox 唯一真相不冲突：不新增完成度账本。
- 与并行执行不冲突：正常模式按子范围裁剪上下文；盲测模式按同一原文复跑。
- 不改历史 patch 目录；本 patch 是后续修正。

## Rationale

输入隔离的价值在于衡量流程或 agent 的未被提示能力，只能用于受控复跑；交付执行的价值在于满足已确认质量约束，必须给必要上下文。双模式让两个目标同时成立且边界可检查：普通任务不得盲派，盲测必须显式标记并保留同一输入。

## Files

- `agents/skills/taskflow/references/implementer-isolation.md` — 改为正常交付 / 盲测复跑双模式
- `agents/skills/taskflow/SKILL.md` — 「实现者隔离」默认正常交付，盲测显式标记
- `agents/skills/taskflow/evals/cases.yaml` — 拆分 normal delivery context 与 blind regression isolation
- `openspec/specs/taskflow-orchestration/spec.md` — 同步 Requirement 与 Scenario（spec 属同步文件，不进本 target patch）

## Validation

- 应用前：`git apply --check --recount agents/skills/taskflow/patches/20260927-093845-isolation-modes/change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；YAML 可解析；`openspec validate --strict --type spec taskflow-orchestration` 通过；grep 确认普通任务不得盲派、盲测必须显式标记；无隐私或样例专有信息。

## Bundle

历史 patch `20260927-090000-delivery-quality-loop/change.patch` 在评审后补了 negative case，未重新生成，不能单独逆向还原当前生产文件。按「不覆盖历史 patch」的纪律，本轮新增 `bundle.patch`：它是从 `a3cf3c6` 到当前 taskflow 生产文件的完整 diff，作为该组改动的 canonical replay。`change.patch` 保留为本轮增量；历史 patch 不改写。
