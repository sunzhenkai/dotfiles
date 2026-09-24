# Decision — 20260925-ledger-write-discipline

decision: promote

状态：用户已确认，候选稿已覆盖生产稿，契约测试复跑 **41 passed**。未 sync、未 commit。

## promote 前置（均满足）

- [x] 用户确认 proposal.yaml 与候选 diff
- [x] eval.md 结论 pass（回归/模式/契约/副作用均过）
- [x] 候选 diff 与 proposal 一致，无夹带编辑

## 已执行动作

1. 候选 `SKILL.md` 覆盖生产 `agents/skills/task-explore/SKILL.md`（+3/-1）
2. 候选 `ledger-write-discipline.md` 复制到 `references/ledger-write-discipline.md`（新增）
3. 候选测试覆盖 `tests/test_task_explore_contract.py`（+23，39→41）
4. `python -m pytest tests/test_task_explore_contract.py -q` → 41 passed

## 待用户决定

- `dotf agents -c` 下发到 `~/.agents/skills/` 镜像
- git 提交本轮改动
