# 校验显式 build 状态

- target: agents/skills/project-spec-mirror
- patch: 20260830-020211-validate-explicit-build-status
- risk: low
- status: proposed

## Intent

确保 `validate` 能拒绝显式写入的非法 `build_status`，同时继续兼容旧镜像缺少该字段时根据 `synced_commit` 推断。

## Conflict check

none。当前实现先调用兼容推断函数，非法显式值会被降级成合法值，导致校验分支不可达；本 patch 只修正该遗漏。

## Rationale

显式状态值和缺失旧字段语义不同：前者应报错，后者需要兼容。分开判断后状态契约才可机械验证。

## Files

- `agents/skills/project-spec-mirror/scripts/specctl.py` — 校验原始显式值。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 增加非法状态回归测试。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
