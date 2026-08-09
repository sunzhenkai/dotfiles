---
name: baseline-ui
description: 通过修复间距、层级、排版和小型布局问题，快速清理粗糙的 UI 代码。适用于界面需要快速清理或打磨时。
---

# 基础 UI

强制执行一套明确的 UI 基线，避免 AI 生成的界面显得粗糙。

## 使用方式

- `/baseline-ui`
  将这些约束应用于本次对话中的所有 UI 工作。

- `/baseline-ui <file>`
  根据以下所有约束审查该文件，并输出：
  - 违规项（引用确切的行/片段）
  - 重要原因（1 句简短说明）
  - 具体修复方案（代码级建议）

## 技术栈

- 除非已有自定义值或被明确要求，否则必须使用 Tailwind CSS 默认值
- 需要 JavaScript 动画时，必须使用 `motion/react`（原 `framer-motion`）
- 在 Tailwind CSS 中，应使用 `tw-animate-css` 实现入场和微动画
- 类名逻辑必须使用 `cn` 工具函数（`clsx` + `tailwind-merge`）

## 组件

- 对于任何具有键盘或焦点行为的内容，必须使用无障碍组件原语（`Base UI`、`React Aria`、`Radix`）
- 必须优先使用项目现有的组件原语
- 同一交互界面中绝不混用组件原语系统
- 若与技术栈兼容，新组件原语应优先使用 [`Base UI`](https://base-ui.com/react/components)
- 纯图标按钮必须添加 `aria-label`
- 除非被明确要求，绝不手动重建键盘或焦点行为

## 交互

- 对破坏性或不可逆操作，必须使用 `AlertDialog`
- 加载状态应使用结构化骨架屏
- 绝不使用 `h-screen`，应使用 `h-dvh`
- 固定元素必须遵守 `safe-area-inset`
- 必须在操作发生处附近显示错误
- 绝不阻止在 `input` 或 `textarea` 元素中粘贴

## 动画

- 除非被明确要求，否则绝不添加动画
- 必须只对合成器属性（`transform`、`opacity`）添加动画
- 绝不对布局属性（`width`、`height`、`top`、`left`、`margin`、`padding`）添加动画
- 除小型局部 UI（文本、图标）外，应避免对绘制属性（`background`、`color`）添加动画
- 入场动画应使用 `ease-out`
- 交互反馈绝不超过 `200ms`
- 循环动画离开屏幕时必须暂停
- 应遵守 `prefers-reduced-motion`
- 除非被明确要求，否则绝不引入自定义缓动曲线
- 应避免为大型图像或全屏界面添加动画

## 排版

- 标题必须使用 `text-balance`，正文/段落必须使用 `text-pretty`
- 数据必须使用 `tabular-nums`
- 密集 UI 应使用 `truncate` 或 `line-clamp`
- 除非被明确要求，否则绝不修改 `letter-spacing`（`tracking-*`）

## 布局

- 必须使用固定的 `z-index` 层级（不使用任意 `z-*`）
- 方形元素应使用 `size-*`，而非 `w-*` + `h-*`

## 性能

- 绝不对大面积 `blur()` 或 `backdrop-filter` 添加动画
- 绝不在线上动画之外应用 `will-change`
- 任何能表达为渲染逻辑的内容都绝不使用 `useEffect`

## 设计

- 除非被明确要求，否则绝不使用渐变
- 绝不使用紫色或多色渐变
- 绝不将发光效果作为主要操作提示
- 除非被明确要求，否则应使用 Tailwind CSS 默认阴影层级
- 空状态必须提供一个明确的下一步操作
- 每个视图的强调色应限制为一种
- 引入新颜色之前，应使用现有主题或 Tailwind CSS 颜色令牌
