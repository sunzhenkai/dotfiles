# task-explore 新增子任务机制（split 阶段 + 嵌套目录 + 原地归档）

- target: agents/skills/task-explore
- mode: update
- patch: 20260921-165730-add-subtask-split
- risk: high
- status: proposed

## Intent

大型探索任务在探索期会分化出多个可独立推进的方向，单个 TASK.md 的目标/决策/未决会被多个方向撑爆，而 handoff 要求冻结方案、不便整包交接。本 patch 新增**子任务**机制：

- 新阶段 `split`：从当前绑定任务拆出子任务（skill 在 explore/chat 中只提示一次，用户确认才建）。
- 子任务 = 完整探索任务，目录嵌套 `ongoing/{parent}/{sub}/`（只一层），`TASK.md` 带 `parent:`，slug 全局唯一。
- 父任务 = 纯伞：只聚合登记，禁止 `handoff`；归档前置为所有子任务已归档，归档时整树搬走。
- 子任务归档为**原地归档**（只改 `status: archived`，不搬目录）；reopen 父任务整树搬回，已 handoff 子任务不自动复活。
- INDEX：子任务任务列写 `{parent}/{sub}`，路径列写嵌套/原地路径；漂移重建下钻一层。
- resume 子任务时先只读父 TASK.md 目标/决策节。

非目标：不改动 taskflow / grilling / openspec 的任何职责；不引入子任务的 promote/摘除动作；不递归嵌套；桥约定（driver 名 = 探索任务 slug + `-driver`）不变。

## Conflict check

- 契约测试 `tests/test_task_explore_contract.py`：`test_index_sync_on_mutating_phases` 的精确字符串需随 SKILL.md 同步加入 `split`；archive/reopen 小节的顺序断言（先查目标已存在、再改状态、再移动）在新文本中保持先后顺序不变。本 patch 同步更新测试并新增子任务契约断言。
- `frontmatter.description` 阶段列表加入 split。
- 与 taskflow 子 change 划界：子任务是探索期概念，二者互不隶属，不产生第二座桥。
- 其余：无（不触碰其它 Skill 职责，无安全/隐私内容）。

## Rationale

经 grill-with-docs 四轮定案：嵌套目录兑现「父目录 = 完整工作包」；原地归档避免 archive 平铺撞名与半棵父树；slug 全局唯一保住桥约定零改动；父禁 handoff 保持「唯一桥」不变形。改动可通过契约测试确定性验证。

## Files

- `agents/skills/task-explore/SKILL.md` — 术语定义、阶段表/加载表 +split、布局、索引、绑定、chat/resume/handoff/archive/reopen 小节、新增 `## \`split\``
- `agents/skills/task-explore/references/task-template.md` — 元信息加 `parent:`，加可选「子任务」小节，原地归档说明
- `agents/skills/task-explore/references/index-template.md` — 子任务行写法与示例
- `agents/skills/task-explore/references/phase-explore.md` — 提示一次可 split
- `agents/skills/task-explore/references/phase-handoff.md` — 父禁 handoff 门禁、子任务原地归档拓扑
- `agents/skills/task-explore/tests/test_task_explore_contract.py` — 更新 INDEX 同步断言；新增 split/术语/门禁/原地归档/嵌套索引契约断言

## Validation

- 应用前：`git apply --check --recount`（仓库根）。
- 应用后：`git diff --check -- agents/skills/task-explore`；`python3 -m unittest` 跑 `tests/test_task_explore_contract.py` 全绿；人工核对 frontmatter、引用路径、无隐私泄露、未触碰历史 patches。
