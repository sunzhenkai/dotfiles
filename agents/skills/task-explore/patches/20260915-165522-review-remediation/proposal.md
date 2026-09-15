# 按 review 修 explore 落点、归档顺序、resume 写入与契约测试

- target: agents/skills/task-explore
- patch: 20260915-165522-review-remediation
- risk: medium
- status: proposed

## Intent

落实对新建 skill 的 review：`explore` 只委托 `grilling`，术语/ADR 由本 skill 写入任务目录，禁止调用 `domain-modeling` / `grill-with-docs`；`archive` 先检查目标路径再改 `TASK.md`；`resume` 改为任务文档只读、INDEX 漂移可修；补文本契约测试。

非目标：不改阶段集合；不在本 patch 里处理 `task-design` 归档搬迁（该目录不在本 skill 生产路径）。

## Conflict check

- 与 `grilling` 无落点冲突；与 `domain-modeling` 的根 `CONTEXT.md` / `docs/adr/` 写入通过「禁止委托」隔离。
- 测试文件名 `test_task_explore_contract.py` 不与现有 skill 测试撞名。

## Rationale

这三项会让 agent 写错仓、留下错误归档状态，或漏掉可验证的门禁；文本契约测试能锁住这些句子。

## Files

- `agents/skills/task-explore/SKILL.md`
- `agents/skills/task-explore/references/phase-explore.md`
- `agents/skills/task-explore/tests/test_task_explore_contract.py`

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/task-explore`；`python3 -m pytest -q agents/skills/task-explore/tests`
