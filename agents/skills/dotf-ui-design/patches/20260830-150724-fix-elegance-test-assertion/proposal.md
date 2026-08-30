# 放宽优雅重构契约测试的「诗意」断言

- target: agents/skills/dotf-ui-design
- patch: 20260830-150724-fix-elegance-test-assertion
- risk: low
- status: proposed

## Intent

上一轮 `20260830-150555-ui-inspect-elegance-mode` 已写入生产文件，但测试用 `assertNotIn("诗意")` 误伤正文里的「不要强制写诗意金句」。改为断言禁止人设原文，并确认保留「不要强制写」收尾约束。不改 `ui-inspect.md` 行为。

## Conflict check

none。只改本 skill 契约测试。不回写上一轮 patch 目录。

## Rationale

低风险、可验证；避免把禁令里的用词当成违规内容。

## Files

- `tests/test_skill_contract.py`：替换过严的 `诗意` 否定断言

## Validation

- `git apply --check --recount` 通过后直接应用
- 应用后跑契约测试
