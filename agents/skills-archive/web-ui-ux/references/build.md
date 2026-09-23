# BUILD 阶段

实现或修改 UI 时执行；自检完成后进入 GATE（见 [gate.md](gate.md)）。

## 1. 读取上下文

先读取：项目规则（`AGENTS.md` / `CLAUDE.md` / `.cursor/rules/*` / `README`）、设计系统（CSS Variables / Tailwind theme / token 文件）、现有页面与组件（避免风格冲突）、可用工具（Playwright / 浏览器 MCP / axe / Lighthouse）。

项目没有设计系统时，先提议最小 token 集（见 [design-tokens.md](design-tokens.md)），不一次性引入大库。

## 2. 设计计划（写代码前必须输出）

- 组件树
- 状态矩阵
- 设计 token 使用方案
- 响应式断点方案
- 交互说明
- 可访问性要求
- 验收标准

需求模糊时按以下默认值假设并明确标注：简洁克制风格（参考 Linear / Stripe / Vercel）；断点 640 / 768 / 1024 / 1280；触控目标 ≥44px；正文 16px / 行高 1.5；对比度 ≥4.5:1；动效 150-300ms ease-out。

## 3. 逐个组件实现

- 每次只实现一个组件或一个明确层级；不一次性生成整页（用户明确要求除外）。
- 顺序：token → 布局 → 组件 → 状态 → 交互 → 可访问性 → 动画。
- 单文件不超过 200 行；不写魔法数字（全部用 token）；不写死宽高；不用绝对定位做主布局。

## 4. 状态矩阵

每个交互组件必须覆盖：default / hover / focus-visible / active / disabled / loading / error / empty / selected。

表单附加：校验中 / 校验失败 / 成功 / 只读。列表与页面附加：加载骨架 / 空状态 / 错误状态 / 无权限状态。

状态要求：

- loading：按钮 loading 且禁用；页面可预测时用骨架屏；超过 300ms 才显示 loading，避免闪烁。
- empty：说明为什么空，并给出下一步按钮。
- error：说明原因，提供重试、返回或联系支持。
- 无权限：说明原因和下一步。
- disabled：视觉明显，且不能点击。
- focus-visible：必须明显，不用 `outline: none`（除非有等效替代）。
- 危险操作：确认或撤销；Toast 不作为唯一反馈，重要错误要持久。

## 5. 交付前自检

运行项目已有命令：lint / typecheck / build / test。如可用，用 Playwright / 浏览器工具截图 375x812、768x1024、1440x900；检查 console、network、横向滚动、Tab 顺序、focus-visible。自检完成进入 GATE。
