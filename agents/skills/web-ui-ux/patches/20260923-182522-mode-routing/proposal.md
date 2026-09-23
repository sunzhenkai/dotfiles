# 拆分入口并支持独立 build / preview 模式

- target: agents/skills/web-ui-ux
- mode: update
- patch: 20260923-182522-mode-routing
- risk: medium
- status: proposed

## Intent

把当前 179 行单文件 SKILL.md 按渐进披露原则重构：入口只保留模式路由与硬约束，细节拆进 references/。同时支持独立触发的阶段模式：

- `build`：单独跑 BUILD（设计计划 → 逐个组件实现 → 自检）+ GATE，不强制进入 REVIEW。
- `preview`：新增只读观察模式——起服务/打开页面 → 多断点截图 → console/network 检查；不改代码，输出观察结果后由用户决定是否进入 build 修复。
- `review`：单独跑独立审查（仍需 GATE 已通过）。
- 默认（未点名阶段）：完整流水线 BUILD → GATE → REVIEW，语义不变。

非目标：不改变 GATE 二元必过语义；不把 skill 升级为自进化结构。

## Conflict check

none。目标无历史 patches、无测试、无其他 Skill 依赖其正文；preview 为只读模式，不破坏 GATE/REVIEW 既有约束。公开性：全部内容为通用前端规则，无个人/内部信息。

## Rationale

token 建议表、验收清单、状态矩阵、响应式/可访问性细则是按需加载内容，塞在入口会稀释每次调用的关键约束（GATE 未过禁止宣布完成、最小改动）。独立 preview 对应"先看效果再决定改不改"的真实工作流，避免为了看一眼页面而被迫跑完整流水线。

## Files

- `agents/skills/web-ui-ux/SKILL.md`：重写为薄入口（模式路由表、全局原则精简、禁止事项精简、references 链接）。
- `agents/skills/web-ui-ux/references/build.md`：BUILD 阶段细节（读取上下文、设计计划输出项、默认假设、组件实现顺序、自检、状态矩阵要求）。
- `agents/skills/web-ui-ux/references/preview.md`：新增 PREVIEW 模式流程（启动方式定位、截图断点、console/network、不改代码、观察报告格式、收尾停服务）。
- `agents/skills/web-ui-ux/references/gate.md`：GATE 必过清单与输出格式（从原正文搬移）。
- `agents/skills/web-ui-ux/references/review.md`：REVIEW 范围、分级、输出格式（从原正文搬移）。
- `agents/skills/web-ui-ux/references/design-tokens.md`：token 建议、响应式、可访问性、内容与边界（从原正文搬移）。
- `agents/skills/web-ui-ux/references/checklist.md`：完成前验收清单（从原正文搬移）。

## Validation

- 应用前：`git apply --check --recount` 通过。
- 应用后：`quick_validate.py`（frontmatter/命名/占位符）、`make registry validate`、`pytest tests/test_agents_skill_defaults.py` 通过；SKILL.md 中所有 references 相对链接目标存在。
