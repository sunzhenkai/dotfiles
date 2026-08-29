# 保持 symbols 跳过原因兼容

- target: agents/skills/project-spec-mirror
- patch: 20260830-021906-preserve-symbol-skip-reasons
- risk: low
- status: proposed

## Intent

让 `symbols` 分别返回既有的 `third_party`、新增的 `ignored` 和新增的 `non_text`，不再把三方路径与二进制文件合并成一个模糊原因。

## Conflict check

none。只细化输出原因，不改变过滤范围。

## Rationale

调用方可能依赖既有 `third_party` 值；稳定、互斥的原因也更利于诊断为什么某个文件没有符号结果。

## Files

- `agents/skills/project-spec-mirror/scripts/specctl.py` — 分离三类跳过分支。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 验证非文本原因。

## Validation

- `git apply --check --recount` 应通过。
- 生产文件 `git diff --check` 应通过。
- 目标 Skill 完整单元测试应通过。
