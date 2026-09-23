---
id: web-ui-ux
name: web-ui-ux
description: "创建、修改或审查 Web UI/UX 时使用。可独立触发：build（实现+自检+GATE）、preview（起服务截图看效果，不改代码）、review（独立审查挑刺）。触发词：UI、UX、页面、组件、样式、响应式、可访问性、设计系统、截图检查、UI 审查、预览。"
---

# Web UI/UX

目标：视觉一致、状态完整、交互清晰、响应式可靠、可访问、可验证、最小改动。优先复用项目已有设计系统与组件库，不自造系统。

## 模式

默认走完整流水线；用户点名某个阶段时只跑该阶段，不自动连带其他阶段。

| 模式 | 何时用 | 做什么 | 详情 |
|------|--------|--------|------|
| build | 实现或修改 UI | 设计计划 → 逐个组件实现 → 自检 → GATE | [references/build.md](references/build.md) |
| preview | 只想先看效果 | 起服务/打开页面 → 多断点截图 → console/network，不改代码 | [references/preview.md](references/preview.md) |
| review | 审查现状 | GATE 通过后独立挑刺，默认不改代码 | [references/review.md](references/review.md) |
| 完整流水线（默认） | 「做好这个页面/组件」类需求 | BUILD → GATE → REVIEW 依次执行 | 上述各 references |

完整流水线顺序：`BUILD → GATE → REVIEW`。GATE 未过禁止进入 REVIEW 或宣布完成；GATE 清单见 [references/gate.md](references/gate.md)。

## 各阶段一句话

- **BUILD**：先出设计计划（组件树、状态矩阵、token 方案、断点、交互、可访问性、验收标准），再逐个组件实现；默认值与状态矩阵要求见 [references/build.md](references/build.md)，token 建议见 [references/design-tokens.md](references/design-tokens.md)。
- **GATE**：二元必过项，FAIL 只修失败项后重过，不做主观审美。
- **REVIEW**：独立审查，目标是挑刺，不是确认完成。
- **preview**：观察模式。发现的问题只汇报（现象 + 位置 + 建议），是否进入 build 修复由用户决定。

## 全局原则

1. 先设计后编码；先组件树后页面；先状态矩阵后样式；先移动端后桌面端。
2. 最小改动，不重写无关文件；每次修改必须可验证。
3. 真实文案，不用 Lorem Ipsum；考虑空 / 超长 / 特殊字符 / 中英混排 / emoji 等边界数据。
4. GATE 未过，禁止进入 REVIEW 或说「完成」。

## 禁止事项

- 不只写 happy path；不忽略空 / 错 / 加载 / 无权限状态与移动端。
- 不用 div 当按钮；不无反馈；不用颜色作为唯一状态提示。
- 不用魔法数字、不写死宽高、不用绝对定位做主布局、不滥用动画、不忽略 focus-visible。
- 不修改无关文件；不在未验证时声称完成。

## 完成前自检

验收清单见 [references/checklist.md](references/checklist.md)。
