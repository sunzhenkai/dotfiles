# ui-inspect 增加交互克制检查项

- target: agents/skills/dotf-ui-design
- patch: 20260830-152507-ui-inspect-interaction-restraint
- risk: medium
- status: proposed

## Intent

在 `ui-inspect` 默认清单增加「交互克制」：检查现有页的交互逻辑是否过重，在复杂度与交互完整性之间取舍，避免过度设计。

要改变的行为：

- 对照清单时多走一块：必要状态（empty / error / loading / disabled）要齐；用户没要求、邻近页也没有的确认层/向导/多入口/叠层反馈记为问题并建议收敛。
- 缺必要状态不算克制，是漏做。
- 默认模式仍不借机重做信息架构或加功能。

非目标：

- 不把 ui-inspect 改成产品/交互设计评审。
- 不替代 `frontend-design` 定新交互范式。
- 不扩大成「只查交互」的独立路由；仍是现有页检查清单的一项。

## Conflict check

与「写组件时逐个检查 hover / focus / active / disabled / loading / empty / error」不冲突：那些是必要状态，本项砍的是可选增强层。与「微交互要短、不主动加弹跳」互补（一个看动效，一个看步骤与控件数量）。不改第三方快照，不改 `patches/` 历史。

## Rationale

AI 落地页常见「为完整而完整」：简单编辑拆多步、叠确认、同一操作多入口。规则跨项目成立、可对照本页与邻近页验证。用户已点名本检查项。

## Files

- `references/ui-inspect.md`：清单新增交互克制；分级补多余交互层；优雅重构禁忌呼应
- `tests/test_skill_contract.py`：断言清单含交互克制与必要状态取舍

## Validation

- `git apply --check --recount` 通过后应用（用户已点名具体检查项）
- 应用后 `git diff --check` 与契约测试
- 隐私检查：无个人路径、账号、密钥
