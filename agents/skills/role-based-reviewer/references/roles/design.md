# UI/UX（`design`，别名 `uiux`）

角色文件：仅在本角色生效时加载（见 [preload-protocol](../preload-protocol.md)）；职责边界以 [role-vocabulary](../role-vocabulary.md) 为准。级别：🔴 Blocker / 🟡 Major（门 3 默认报）/ ⚪ 默认不报，拿不准降一级。

来源：参考 vercel-labs/web-interface-guidelines（可静态判定规则）、anthropics/frontend-design（微文案与 anti-slop）与 Nielsen/WCAG 启发式改写。

## 优先锚点

UI 源码/样式、设计规范、可访问性相关实现、组件库与 design token 定义。

跳过：后端逻辑、部署。

## 核心检查清单

判定方式：`[代码]` 读 diff/源码可判；`[运行态]` 必须渲染后确认。纯 diff 评审中 `[运行态]` 条目降级为「⚠ 需运行态验证」提示，不做判定、不装能判；不为此启动服务或截图。Blocker 门槛 = quality floor：键盘可达、focus 可见、破坏性操作有确认或 undo、空态不崩、表单错误有反馈、尊重 reduced-motion。

### 1. 交互流程

1. 🔴 [代码] 破坏性操作（删除、批量操作、发布、资金类）必须二次确认或可 undo，never immediate
2. 🟡 [代码] 表单/按钮防重复提交：请求中禁用并给反馈，失败后恢复可点
3. 🟡 [代码] URL 反映状态：筛选、分页、tab、展开面板可深链，刷新/分享不丢状态
4. 🟡 [代码] 多步流程可取消、可返回；modal 有 Esc/关闭路径且不丢已填数据
5. 🟡 [代码] 离开有未保存改动时给出警告
6. ⚪ [代码] 操作后有明确结果反馈（toast/行内确认），说清发生了什么
7. ⚪ [运行态] 主任务流程实际走通（每步：知道做什么 → 看到怎么做 → 理解反馈 → 确认成功）

### 2. 信息架构

8. 🟡 [代码] heading 层级有序不跳级（h1→h2→h3）
9. 🟡 [代码] landmark 语义正确：`header`/`nav`/`main`/`aside`/`footer`
10. ⚪ [代码] 长页面有 skip link；导航有当前位置指示（面包屑/高亮当前项）
11. ⚪ [运行态] 视觉层次：最重要内容最突出，阅读顺序可追踪

### 3. 可用性启发式（Nielsen 压缩版）

12. 🟡 [代码] 系统状态可见：异步操作有 loading/进度/结果反馈
13. 🟡 [代码] 贴近用户语言：错误消息不用内部术语、裸错误码、堆栈（"Error 500" 是违规范例）
14. 🟡 [代码] 用户控制与自由：可取消、可返回、可撤销（入口与文案存在性；流程细节见第 1 节）
15. 🟡 [代码] 一致性与标准：同一动作全程同名同图标；同类任务用同模式
16. 🟡 [代码] 错误预防优先于报错：输入约束、格式 mask、智能默认值、危险操作 disabled 态
17. 🟡 [代码] 错误恢复：错误消息指明问题 + 给出修复建议（如 "Email format should be: user@example.com"）
18. ⚪ [代码] 识别而非记忆：icon 有 label/tooltip；常用项/最近项可见
19. ⚪ [代码] 效率：高频操作有快捷键或批量操作
20. ⚪ [代码] 极简：渐进披露，无与任务无关的信息
21. ⚪ [代码] 帮助与文档：复杂表单有 contextual help、示例或 tooltip

### 4. 无障碍

22. 🔴 [代码] 交互元素键盘可达：无键盘陷阱；modal/菜单打开后焦点进入、关闭后归还触发元素
23. 🔴 [代码] 禁裸 `outline-none`：有可见 focus 样式（`:focus-visible`）；sticky 浮层不遮挡 focus 元素
24. 🟡 [代码] icon-only 按钮/链接有 `aria-label`；语义 HTML 优先于 ARIA（`<button>` 而非 `<div onClick>`）
25. 🟡 [代码] 图片 `alt` 语义化；纯装饰图 `alt=""` + `aria-hidden`
26. 🟡 [代码] async 状态变更（toast、校验结果）走 `aria-live="polite"`
27. 🟡 [代码] 动效尊重 `prefers-reduced-motion`；手势操作有 tap/键盘替代
28. 🟡 [代码] touch target ≥24px（WCAG 2.2）/ 44px（Apple HIG）
29. 🟡 [代码] 文本/背景对比度：正文 ≥4.5:1、大字 ≥3:1（代码查 token 色值对；实际渲染仍需运行态确认）
30. ⚪ [代码] 表单控件有关联 label；状态/错误不用颜色单独编码（有图标或文案冗余）
31. ⚪ [运行态] 屏幕阅读器走查、200% 缩放、320px reflow

### 5. 视觉与一致性

32. 🟡 [代码] 颜色/间距/圆角/阴影/字体走 design token，diff 中不新增硬编码值
33. 🟡 [代码] 语义色全程一致：错误=红、成功=绿、警告=黄，不混用
34. 🟡 [代码] 同类组件与既有组件 API/命名/组织一致；重复实现应复用而非新造
35. ⚪ [代码] anti-slop：无生成式默认 tell——奶油底+高对比 serif+陶土 accent、近黑底+单一荧光色、tracked-out 全大写 eyebrow label、中点连接的 meta 串、`#0B0B0F` 假黑、链接后挂 `→` 装饰
36. ⚪ [运行态] 间距/对齐/排版实际渲染层次、字体加载闪烁（FOIT/FOUT）

### 6. 响应式与适配

37. 🟡 [代码] 图片/媒体显式 `width`/`height` 防 CLS；屏下图 `loading="lazy"`
38. 🟡 [代码] 长内容防御：`truncate`/`line-clamp`/`min-w-0`，无水平滚动溢出
39. 🟡 [代码] 大列表（>50 行）虚拟化或分页，不做无界 `.map()`
40. 🟡 [代码] 移动优先：媒体查询用 `min-width`；正文 ≥16px
41. ⚪ [代码] `env(safe-area-inset-*)`；模态内 `overscroll-behavior: contain`；禁 `transition: all`，只动画 `transform`/`opacity`
42. ⚪ [运行态] 375/768/1280 三断点实测：布局是重组而非等比缩小

### 7. 微文案

43. 🟡 [代码] CTA 动词具体、说清发生什么（"Save changes" 而非 "Submit"/"Continue"）
44. 🟡 [代码] 错误消息含修复路径，不道歉、不模糊（禁止只说一句 "Something went wrong"）
45. 🟡 [代码] 空态文案是行动邀请：说清这是什么、下一步做什么
46. ⚪ [代码] 动作名跨流程一致（Publish 按钮 → 结果提示 "Published"）
47. ⚪ [代码] 主动语态、第二人称、sentence case；禁 "click here"
48. ⚪ [代码] 排版字符正确：省略号 `…` 非 `...`、弯引号、加载文案以 `…` 结尾

### 8. 状态覆盖

49. 🔴 [代码] 每个数据区四态齐全：loading / empty / error / success——空数据不得渲染破 UI
50. 🟡 [代码] 表单字段态齐全：empty / filled / error / success / disabled
51. 🟡 [代码] 交互元素态齐全：hover / focus / active / disabled
52. 🟡 [代码] 极端数据防御：空字符串、单条、超长文本、UGC 短/均/超长三档
53. 🟡 [代码] dark mode 走 token 非硬编码；`theme-color` meta 与暗色阴影同步调整
54. ⚪ [代码] hydration 安全：日期/客户端值渲染有守卫，无 SSR mismatch
55. ⚪ [运行态] 各状态实际渲染、dark mode 实测

## 下游建议

`ui-template-design` → UI 模板与设计规格生成；修复类结论交回常规实现流程。

## 跨角色 redirect

- design ↔ product（体验）：视觉/交互/无障碍 → design；价值/范围/文案 → product
- design ↔ engineer（UI 落地）：视觉与交互规格 → design；实现与性能 → engineer
