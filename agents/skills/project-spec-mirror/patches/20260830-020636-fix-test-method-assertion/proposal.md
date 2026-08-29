# 修复测试方法语义断言

- target: agents/skills/project-spec-mirror
- patch: 20260830-020636-fix-test-method-assertion
- risk: low
- status: proposed

## Intent

把 contract 测试对连续短语 `测试方法只简述` 的要求改为断言 detailed 方法表中的结构语义 `测试方法 | 只简述`。

## Conflict check

none。生产文档仍明确要求测试方法只简述；只移除对具体排版连接方式的错误依赖。

## Rationale

契约测试应验证规则存在，而不是强制某一句话的空格和表格排版。

## Files

- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 更新一条断言。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- 目标 Skill 完整单元测试应通过。
