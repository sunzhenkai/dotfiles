# 修复 build 步骤编号

- target: agents/skills/project-spec-mirror
- patch: 20260830-020251-fix-build-step-number
- risk: low
- status: proposed

## Intent

把 build 工作流最后一个重复的步骤编号 `9` 修正为 `10`。

## Conflict check

none。只修正文档编号，不改变行为。

## Rationale

连续编号能避免引用步骤时产生歧义。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 修正一个编号。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- 目标 Skill 完整单元测试应通过。
