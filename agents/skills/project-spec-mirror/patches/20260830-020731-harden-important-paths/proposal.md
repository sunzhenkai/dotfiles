# 强化 important 路径校验

- target: agents/skills/project-spec-mirror
- patch: 20260830-020731-harden-important-paths
- risk: low
- status: proposed

## Intent

修复 `normalize_source_paths` 先剥离 `/`、导致绝对路径可能被误当成相对路径的问题，并让 `validate` 同时检查状态文件中的 important 路径是否安全且已规范化。

## Conflict check

none。只收紧新增字段既定的“源相对路径”契约。

## Rationale

important 范围必须稳定、可移植且不能逃出 source。写入门禁和状态校验都应拒绝绝对路径、父目录穿越及空路径。

## Files

- `agents/skills/project-spec-mirror/scripts/specctl.py` — 修正路径规范化并复用于 validate。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 增加绝对路径和状态穿越回归测试。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- 目标 Skill 完整单元测试应通过。
