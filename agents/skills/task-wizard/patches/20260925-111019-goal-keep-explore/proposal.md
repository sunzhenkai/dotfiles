# Goal 模式复杂档不跳过 explore 阶段

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-111019-goal-keep-explore
- risk: medium
- status: proposed

## Intent

Goal 方案复杂档路由到 task-explore 时，按 `new` → `explore` → `design` → `decide` → `handoff` 逐阶段推进，不跳阶段。登记进 `TASK.md`「方案」的 wizard 方案是 `explore` 的输入，不是冻结结论。触发场景：goal 里评审收敛后命中复杂档。非目标：任务方案（非 goal）路径本就走 `explore`/`design`/`decide`，不改；冻结时刻 `decide` 完立刻 `handoff` 的衔接不变；`explore` 不重复方案里已查证的事实与外部参照。

## Conflict check

- 与 task-explore 的阶段表（new/explore/design/decide/handoff）与 goal 模式「确认走 task-wizard 审阅」一致；无职责冲突。
- SKILL.md「不重演探索」一句会被读成「跳过 explore」，与本意图矛盾，同 patch 改为「不重复已查证的摸底」。
- 复杂度路由表（任务方案路径）已写 `explore`/`design`/`decide`，无需改。none 其余。

## Rationale

wizard 方案是步骤级纲要，复杂档（项目级重构、逻辑重塑）需要 task-explore 的探索与设计来拷问未决分支；goal 模式减少的是确认次数，不是探索深度。改动可验证：路由字符串逐字写进 Goal 方案，读方案即可核。

## Files

- agents/skills/task-wizard/SKILL.md — 复杂档 Goal 路由字符串改为逐阶段推进；「不重演探索」改为「不重复已查证的摸底」

## Validation

- `git apply --check --recount`
- `git diff --check -- agents/skills/task-wizard`
- 核对实际 diff 与 proposal 一致；frontmatter 合法；无隐私泄露；未触历史 patches/
