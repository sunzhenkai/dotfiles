# task-explore：补齐 reopen 阶段细则

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-173640-reopen-phase-detail
- risk: medium
- status: proposed

## Intent

`reopen` 是与 `archive` 对称的另一次整树搬家，却仍留在 SKILL.md 的 7 行步骤里，加载表把它归在「本文件已够」。本轮按 archive 的同构方式补齐：新建 `references/phase-reopen.md`（定位分支 + 4 条门禁 + 6 步），SKILL.md 只留不可跳过的硬门禁。

修的实质问题：

- **索引谎报**：`SKILL.md` 索引小节要求 `handed-off` 行一句话以 `→ {task-name}-driver` 结尾，而 reopen 第 6 步却写「`handed-off` 任务 INDEX 行不动」。撤回交接后任务已不是 handed-off，尾注留在索引里就是错的。细则改为：行留在 Ongoing，但去掉尾注。
- **状态与目录位置混为一谈**：原步骤按「在 archive 还是 ongoing」判断形态，INDEX 漂移时会误判。改为以 `TASK.md` 的 `status` 为准，定位前先按索引规则重建。
- **历史字段无处安放**：补 `reopened: YYYY-MM-DD`，并规定保留 `archived:` 作历史，决策/交接/归档记录不删不改写。
- **driver 侧现状不看**：与 archive 对称，撤回或复活前报告 driver 是否仍在、openspec 进度或已归档状态，读不到写「进度未知」，一律不删 driver 及其 change。
- **子任务名撞车**：`{sub}` 全局唯一只在 `split` 校验；整树搬回时可能与别的父任务的子任务重名，导致 `{sub}-driver` 撞车。补搬回前扫描。
- **`SUMMARY.md` 归宿**：随树搬回、原样保留不改写，下次归档按 archive 细则续写，避免叙述被重写。

非目标：不动 archive 细则与本会话已应用的 `20260924-172023-archive-phase-detail-gates`；不加批量 reopen 语义（逐个走）；不改 `chat` / `resume`；不做 `tasks/` 存量数据迁移。

## Conflict check

- 与 `SKILL.md` 索引小节：本轮把「去尾注」写进 reopen，正是为消除与索引节规则的相互矛盾，不改索引节本身。
- 与 archive 的 `## 批量归档` 语义：reopen 明确声明逐个走，不与 archive 对称扩展，避免同一轮里两处引入未验证规则。
- 与 `references/task-template.md` 的 status 说明：追加一句 `reopened` 元信息，字段与 phase-reopen.md 一致，不新增骨架小节。
- 与 openspec `task-explore-lifecycle` spec：spec 未写 reopen 细则（只写 handoff/archive），本轮不与之冲突。

## Rationale

reopen 与 archive 同为整树搬家且同样易产生索引漂移；archive 已在上一轮得到细则与契约测试，reopen 仍是散文式步骤，其中「INDEX 行不动」与索引节直接冲突，会让后续会话继续按 handed-off 找 driver。改动均可文本验证，由 `tests/test_task_explore_contract.py` 锁住（scratch 预跑 39 passed）。

## Files

- `agents/skills/task-explore/SKILL.md` — 加载表新增 reopen 行、末行收回 `chat / resume`；reopen 段 7 步瘦成 4 条硬门禁 + 指向 reference
- `agents/skills/task-explore/references/phase-reopen.md` — 新建：定位 3 步 + 门禁 4 条 + 步骤 6 步
- `agents/skills/task-explore/references/task-template.md` — status 说明补 `reopened: YYYY-MM-DD`
- `agents/skills/task-explore/tests/test_task_explore_contract.py` — 顺序不变量测试改读 reference；新增 6 个 reopen 契约测试；reference 清单与按需加载断言同步

## Validation

- 应用前：`git apply --check --recount agents/skills/task-explore/patches/20260924-173640-reopen-phase-detail/change.patch`
- 应用后：`git diff --check`；`python3 -m pytest agents/skills/task-explore/tests -q` 全绿；`grep -n "INDEX 行不动" SKILL.md` 无命中；无隐私内容
