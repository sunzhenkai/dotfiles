# 添加现有页 UI 细节检查 phase

- target: agents/skills/dotf-ui-design
- patch: 20260830-150023-add-ui-inspect-phase
- risk: medium
- status: proposed

## Intent

为 `dotf-ui-design` 增加自有 phase `ui-inspect`：对**已有页面**做空间与对齐细节检查并按优先级打磨，而不是再开一条上游能力 skill。

要改变的行为：

- 触发：用户点名检查/打磨现有页的间距、分割线、内容块 padding、图标与按钮位置、整体布局时，进入本 skill 并只走 `ui-inspect`。
- 整页流水线：实现之后、`webapp-testing` 验收之前插入 `ui-inspect`。
- 模型按 `references/ui-inspect.md` 取证、对照清单、分级记录、修复、复检。

非目标：

- 不替代 `frontend-design`（视觉方向 / 新身份）。
- 不替代 `webapp-testing`（Playwright 工具链）。
- 不替代 `tailwind-css-patterns`（如何写间距实现）。
- 不把 `ui-inspect` vendor 成第五条内部引用 skill，也不安装到全局。
- 不为「把这个按钮改成红色」这类单点改 class 自动加载。

## Conflict check

与现有「薄路由器 + 一次只加载一个能力 skill」不冲突：`ui-inspect` 是本 skill 自有清单，不占能力槽；需要截图或改 Tailwind 时仍串行加载对应能力 skill、用完即弃。

不修改 `references/` 下第三方快照，不改 `UPSTREAM.md`，不改 `patches/` 历史。不与 `pretty-view-html` / `pretty-view-ppt` 抢路径。`内置准则` 仅补一条交付前对照清单，不另起设计体系。

## Rationale

AI 落地的页面常见问题集中在空间节奏（相邻 gap 混用、分割线一侧贴死、卡片 padding 不齐、图标/按钮光学偏位），现有能力 skill 分别覆盖「方向 / token / 写法 / 截图」，缺一条可执行的检查流程。清单跨项目成立：跟项目刻度，没有则 4px 基数；可用截图或源码复检，契约测试可断言文件与路由字样存在。

## Files

- `SKILL.md`：description、门 1、流水线、路由说明纳入 `ui-inspect`
- `references/catalog.md`：声明自有 phase，更新整页顺序
- `references/ui-inspect.md`：检查流程、清单、输出契约（新建）
- `tests/test_skill_contract.py`：断言自有清单存在且未 vendor 成 skill 目录

## Validation

- `git apply --check --recount` 通过后再按中风险门禁确认
- 应用后 `git diff --check` 与 `python3 -m pytest agents/skills/dotf-ui-design/tests/test_skill_contract.py`
- 隐私检查：无个人路径、账号、密钥
