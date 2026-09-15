# 修正 handoff 契约测试断言

- target: agents/skills/task-explore
- patch: 20260915-170639-fix-handoff-contract-assert
- risk: low
- status: proposed

## Intent

把契约测试里的「不要发明」改成与 `phase-handoff.md` 一致的「不发明」。不改正文。

## Conflict check

none

## Rationale

断言应锁住已有措辞，不应逼正文改成测试用词。

## Files

- `agents/skills/task-explore/tests/test_task_explore_contract.py`

## Validation

- `git apply --check --recount`
- `python3 -m pytest -q agents/skills/task-explore/tests`
