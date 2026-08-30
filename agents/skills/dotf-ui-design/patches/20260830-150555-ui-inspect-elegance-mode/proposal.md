# ui-inspect 增加可选优雅重构模式

- target: agents/skills/dotf-ui-design
- patch: 20260830-150555-ui-inspect-elegance-mode
- risk: medium
- status: proposed

## Intent

在已有 `ui-inspect` 空间检查之上，增加可选模式「优雅重构」（Web Elegance Refactor）。默认行为不变：只查间距、分割线、padding、图标按钮、整体布局。

仅当用户明确要求优雅重构、换气质、赋予呼吸感时，才走 4 阶段：听诊 → 处方 → 手术 → 点睛。阶段二默认不换色、不换字；用户明确允许换视觉语言时才给 1 个具名风格，并提示必要时先走 `frontend-design`。

吸收：呼吸感、降噪、克制微交互、反 AI 模板套餐、禁花哨动画、禁引入大型字体/图标库。不写入「20 年治愈师」人设，不强制诗意收束句。

非目标：不替代 `frontend-design` 做新页面/新视觉身份；不把默认检查改成强制 4 阶段输出；不原样粘贴用户草稿。

## Conflict check

与「不另起视觉语言」的默认检查不冲突：换色换字有明确门闩。与 `frontend-design` 的边界写清：新方向走它，现有页气质打磨走本模式。不改第三方快照，不改 `patches/` 历史。

## Rationale

用户选定「可选模式」而非原文整段写入。4 阶段可执行、可复检；禁忌跨项目成立。公开 skill 不承载戏剧人设与不可验证的诗意句。

## Files

- `references/ui-inspect.md`：默认清单补呼吸/降噪/微交互；新增优雅重构 4 阶段与禁忌
- `SKILL.md`：触发与路由区分默认检查 vs 优雅重构
- `references/catalog.md`：单点路由补优雅重构
- `tests/test_skill_contract.py`：断言可选模式与默认检查并存

## Validation

- `git apply --check --recount` 通过后应用（用户已选定具体落地方式）
- 应用后 `git diff --check` 与契约测试
- 隐私检查：无个人路径、账号、密钥
