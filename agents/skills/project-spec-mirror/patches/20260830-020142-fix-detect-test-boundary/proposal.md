# 修复 detect 测试异常边界

- target: agents/skills/project-spec-mirror
- patch: 20260830-020142-fix-detect-test-boundary
- risk: low
- status: proposed

## Intent

修正上一 patch 新增的测试隔离写法：在 mock 掉祖先 project 探测后，直接断言 `detect_layout` 抛出的 `SpecError.reason`，不再错误地假设直接调用 `cmd_detect` 会经过 CLI 的 JSON 异常边界。

非目标：不修改生产代码、project 探测策略或状态生命周期行为。

## Conflict check

none。该测试仍验证“没有当前或祖先 project，也没有 project/source 参数时必须报 `project_required`”，仅把断言放到正确的函数边界。

## Rationale

`main` 负责把 `SpecError` 转成 JSON；单元测试 mock 的是进程内函数，应该直接断言异常。该修复确定性强且不改变生产行为。

## Files

- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 改为断言 `detect_layout` 的 `SpecError.reason`。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
