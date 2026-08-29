# 修复主流程模式契约断言

- target: agents/skills/project-spec-mirror
- patch: 20260830-020705-fix-main-mode-contract
- risk: low
- status: proposed

## Intent

移除 contract 测试对主 `SKILL.md` 重复 reference 文案 `完整逻辑` 的要求，改为验证主流程包含“深入行为承载符号”和“测试只写覆盖意图”，详细写法仍由 `modes.md` 单一维护。

## Conflict check

none。主流程继续链接 `modes.md`，没有降低核心方法的详细度要求。

## Rationale

主 Skill 应保留路由和关键工作流，详细方法格式放 reference；测试不应迫使两处复制同一句规则。

## Files

- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 更新两条主流程语义断言。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- 目标 Skill 完整单元测试应通过。
