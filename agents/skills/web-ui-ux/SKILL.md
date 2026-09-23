---
id: web-ui-ux
name: web-ui-ux
description: "创建、修改或审查 Web UI/UX 时使用。一个 Skill 两个阶段：BUILD 实现并自检，GATE 薄门禁，REVIEW 独立审查。触发词：UI、UX、页面、组件、样式、响应式、可访问性、设计系统、截图检查、UI 审查。"
---

# Web UI/UX Skill

本 Skill 是一条流水线，必须按阶段执行：

```
PHASE 1  BUILD  →  GATE  →  PHASE 2  REVIEW
```

不允许跳过阶段，不允许 GATE 未通过就进入 REVIEW 或宣布完成。

## 角色

你是资深前端工程师 + UI/UX 工程师。目标是视觉一致、状态完整、交互清晰、响应式可靠、可访问、可验证、最小改动。

## 全局原则

1. 先设计，后编码。
2. 先组件树，后页面。
3. 先状态矩阵，后样式。
4. 先移动端，后桌面端。
5. 优先使用项目已有设计系统和组件库。
6. 最小改动，不重写无关文件。
7. 每次修改必须可验证。
8. GATE 未过，禁止进入 REVIEW，禁止说“完成”。

---

# PHASE 1 — BUILD

## 1.1 读取上下文

先读取项目规则、设计系统、现有组件、可用工具。  
没有设计系统时，先提议最小 token 集，不引入大库。

## 1.2 先输出设计计划

写代码前必须输出：

- 组件树
- 状态矩阵
- 设计 token 使用方案
- 响应式断点方案
- 交互说明
- 可访问性要求
- 验收标准

需求模糊时按默认值假设并标注：简洁克制风格；断点 640/768/1024/1280；触控目标 ≥44px；正文 16px / 行高 1.5；对比度 ≥4.5:1；动效 150-300ms。

## 1.3 逐个组件实现

- 每次只实现一个组件或一个明确层级。
- 顺序：token → 布局 → 组件 → 状态 → 交互 → 可访问性 → 动画。
- 单文件不超过 200 行。
- 不写魔法数字、不写死宽高、不用绝对定位做主布局。

## 1.4 交付前自检

实现完成后，运行项目已有命令：lint、typecheck、build、test。  
如可用，用 Playwright / Browser：截图 375x812、768x1024、1440x900；检查 console、network、横向滚动、Tab 顺序、focus-visible。

自检完成后进入 GATE。

---

# GATE — 薄门禁

GATE 是一组二元必过项。**任何一项 NO，必须回到 PHASE 1 修复，禁止进入 PHASE 2，禁止输出“完成”。**

GATE 只检查客观、可验证、快速的项目，不做主观审美，不做全面审查。

## 必过清单

- [ ] lint 通过
- [ ] typecheck 通过
- [ ] build 通过
- [ ] 本次组件状态覆盖：default / hover / focus-visible / active / disabled / loading / error / empty
- [ ] 375px 和 1440px 截图已生成
- [ ] 无横向滚动
- [ ] console 无新增 error
- [ ] network 无新增 error
- [ ] 键盘可操作，focus-visible 可见
- [ ] 表单错误靠近字段且 aria 基本正确
- [ ] 未修改无关文件

## GATE 输出格式

```md
## GATE
- lint: PASS / FAIL
- typecheck: PASS / FAIL
- build: PASS / FAIL
- 状态覆盖: PASS / FAIL（缺失：...）
- 截图: PASS / FAIL
- 横向滚动: PASS / FAIL
- console: PASS / FAIL
- network: PASS / FAIL
- 键盘/focus: PASS / FAIL
- 表单 aria: PASS / FAIL
- 无关文件: PASS / FAIL

结果：PASS → 进入 PHASE 2 / FAIL → 回到 PHASE 1
```

FAIL 时只修复失败项，修复后重新过 GATE。

---

# PHASE 2 — REVIEW

只有 GATE 通过后才能进入。REVIEW 是独立审查，目标是挑刺，不是确认完成。

## 2.1 审查范围

- 整个页面、流程、项目，不只本次改动。
- 多断点：375 / 768 / 1024 / 1440。
- 多状态：default / hover / focus / active / disabled / loading / error / empty / success / 无权限。
- 内容与边界：空、超长、特殊字符、中英混排、emoji、金额、日期、手机号格式。
- 可访问性：axe / 语义标签 / aria / 对比度 / 焦点管理 / 模态焦点锁定。
- 视觉一致性：token、间距、字号、圆角、阴影、对齐。
- 交互：反馈、确认、撤销、乐观更新、loading 阈值。
- 性能：Lighthouse、布局抖动、不必要的重渲染。

## 2.2 问题分级

- P0：阻断、不可用、严重错位、不可访问。
- P1：明显体验问题、状态缺失、响应式错误。
- P2：打磨、间距、对齐、动效。

## 2.3 输出格式

```md
## REVIEW

### P0
- 问题：
- 位置：
- 根因：
- 建议：
- 验证方式：

### P1
...

### P2
...

### 结论
- 可交付 / 需修复后交付 / 不可交付
```

REVIEW 默认不改代码。如需修复，只做最小修复，并重新过 GATE。

---

# 禁止事项

- 不跳过阶段，不跳过 GATE。
- 不在 GATE FAIL 时进入 REVIEW 或宣布完成。
- 不只写 happy path。
- 不忽略移动端。
- 不用 div 当按钮。
- 不无反馈。
- 不用魔法数字、不写死宽高。
- 不滥用动画。
- 不忽略 focus-visible。
- 不修改无关文件。
- 不在未验证时声称完成。

# 一句话执行准则

BUILD 实现并自检 → GATE 二元必过 → REVIEW 独立挑刺。  
GATE 未过，禁止前进。  
每阶段只做本阶段的事，最小改动，可验证。
