# task-explore：handoff 与 archive 解耦 + 子任务多次交接

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-154507-decouple-handoff-archive
- risk: high
- status: proposed

## Intent

handoff 不再归档：交接后任务转入 `handed-off`（留在 `tasks/ongoing/`、INDEX 可见、可 resume、不清绑定），archive 回归「确认关闭」语义（含 handed-off 后收尾，归档时警告 driver 可能仍在）。配套收紧：

- handoff 目标自动推断：绑定子任务→交接它；绑定父任务→批量自动交接所有「已 decide 未交接」子任务，零就绪打断，失败即停不回滚；父永不建 driver。
- 父任务纯伞化：`status` 恒 `ongoing`，decide 仅限范围/非目标/拆分原则；archive 门禁放宽为「所有子任务 ∈ {handed-off, archived} + 确认无需回溯」。
- decide 版本化：重复 decide 追加编号、旧决策标「被 D-n 取代」；handed-off 后重新 decide 须先 reopen 撤回交接；未决默认值逐条经用户确认。
- 写盘边界：评审/委派产物只写 `{taskRoot}`，禁止 `tasks/` 根级新目录。
- 删除「子任务原地归档 / 原地 reopen」特例（handoff 不归档后失去存在理由）。

非目标：不改 taskflow 侧；不做 driver→探索任务的状态回写；不迁移存量 archived 任务。

## Conflict check

与现有 SKILL.md 的耦合点（handoff 段、archive 门禁、reopen 段、子任务原地归档、decide 写入）冲突即为本次意图，已整体重排；与其它 skill（taskflow / agent-roster）职责无重叠——桥保持单向，taskflow 无改动。

## Rationale

真实事故（sage agent-web-rebuild）：handoff 归档后 INDEX Ongoing 清空，用户与后续会话误判任务死亡；归档后的 plan-review 发现 P0 只能越界写 `tasks/reviews/`。状态机把「换账本」与「生命周期终止」耦合是根因；用户已逐条裁决（grill Q1-A、Q2-C、Q3/Q4/Q5/Q6 按推荐）。

## Files

- `agents/skills/task-explore/SKILL.md` — description、术语、阶段表、INDEX/布局约定、decide/handoff/archive/reopen/split 段
- `agents/skills/task-explore/references/phase-handoff.md` — 重写：目标自动推断、单任务门禁、父任务批量交接
- `agents/skills/task-explore/references/phase-decide.md` — 未决默认值逐条确认、重复 decide、父 decide 边界
- `agents/skills/task-explore/references/phase-plan-review.md` — 评审产物落盘边界
- `agents/skills/task-explore/references/index-template.md` — handed-off 行与父聚合、子任务归档示例
- `agents/skills/task-explore/references/task-template.md` — status 枚举与 handed-off 元信息

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter name 与目录一致；references 链接存在（phase-decide.md → task-template.md 相对路径保持）；无隐私内容；`openspec validate task-explore-decouple-handoff-archive --strict` 通过（对应 openspec change 的 6.2 通读核对）
