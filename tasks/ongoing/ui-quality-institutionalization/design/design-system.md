# Project Design System

本设计只约束当前任务管理平台；共享 skill 只抽象“UI contract 必须存在与如何验收”，不复制本文的像素、类名或页面名。

## Architecture

```text
         ┌────────────────────────────┐
         │ docs/ui/design-system.md   │  人类可读契约
         └──────────────┬─────────────┘
                        │
        ┌───────────────┴───────────────┐
        │ tokens: color / space / type  │
        │ control / radius / shadow     │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │ primitives: Button / IconBtn  │
        │ Input / Select / Textarea     │
        │ Field / Checkbox / ActionLink │
        │ Chip / Badge / Overlay        │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │ page patterns: topbar / form  │
        │ drawer / modal / board / list │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │ evidence + tests             │
        │ DOM metrics / screenshots    │
        └──────────────────────────────┘
```

## Token contract

### Spacing

使用 4px 基础节奏：

```text
space-1 = 4px
space-2 = 8px
space-3 = 12px
space-4 = 16px
space-5 = 24px
space-6 = 32px
```

规则：

- 组件内部与页面 padding 只能取 token。
- 同一容器的子项 gap 必须一致。
- 不允许业务 JS 新增 inline `margin` / `padding` / `gap`。

### Control dimensions

| Token | 用途 | 当前项目值 |
|---|---|---|
| `--control-h` | 常规表单 / 普通按钮 | 36px |
| `--control-h-sm` | 顶栏、详情属性、行内操作 | 32px |
| coarse pointer | 触控目标 | ≥40px |

规则：

- 同一行、同一区域内的 Button / Input / Select 必须同高。
- dense 区域不得混用 regular 与 dense 控件。
- 触控模式下所有可操作目标统一提升，不允许零散例外。

### Typography

- 正文：14px / 1.55
- secondary：12-13px
- micro label：11-12px
- 数字：tabular-nums
- 标题层级保持现有页面结构，不新造装饰性 heading。

### Color / border / radius / shadow / z-index / motion

- 语义色继续使用 `accent / danger / warn / ok / surface / text`。
- 新 UI 不写裸 hex；例外必须进 contrast audit。
- radius：`4px / 5px / 8px / 14px` 对应微控件、输入、普通卡片、大浮层。
- shadow 分 `sm / md / lg`。
- z-index 分页面内容、sticky、drawer、modal、toast。
- motion 只用短时长 background / border / transform / opacity，尊重 reduced motion。

## Primitive / composite coverage

契约覆盖所有已盘点组件；实施按切片推进，未迁移不等于永久推迟，也不构成生产性降级。

| Slice | 组件 | 契约状态 | 实施状态 |
|---|---|---|---|
| 1 | Button、IconButton、Input、Select、Textarea、Field、Checkbox、ActionLink | 本设计定义 | 首个实现切片全部迁移 |
| 2 | Chip、Badge、Card、Overlay（Modal / Drawer）、Toast、EmptyState、ErrorState、Skeleton、Table / List row | 本设计定义代表性契约 | 第二个实现切片迁移 |
| 3 | Dashboard 图表、看板拖拽、审计 / 回收站等页面特有模式 | 由页面模式与证据矩阵约束 | 第三个实现切片收敛 |

任何组件若本轮只做契约、未完成迁移，必须在验证记录中列为剩余实现项；不得把它说成已满足完成判据。

## Primitive contracts

### Button

```text
variants:
  primary    主行动
  secondary  普通行动
  ghost      低强调行动
  danger     破坏性 / 风险行动
sizes:
  md = --control-h
  sm = --control-h-sm
states:
  default / hover / active / focus-visible / disabled / pending
forbidden:
  inline height
  ad-hoc padding
  hover underline
  layout-shifting hover
```

### Input / Select / Textarea

```text
sizes:
  regular = --control-h
  dense = --control-h-sm
states:
  default / focus-visible / filled / invalid / disabled / readonly
layout:
  width follows parent field or control row
  Select arrow must not shrink text area
  Textarea keeps vertical resize and minimum height
```

### Field

```text
structure:
  label + control + hint / error
rules:
  label associated with control
  error appears in one stable location
  invalid state does not shift layout
```

### IconButton

```text
states:
  default / hover / focus-visible / disabled
rules:
  square dimensions from control token
  icon-only requires aria-label
  touch size follows coarse-pointer token
  disabled does not retain hover background
```

### Checkbox

```text
structure:
  native input + associated label
states:
  checked / unchecked / indeterminate where used / focus-visible / disabled
rules:
  label click toggles control
  touch target includes label and input
  visual state is not color-only
```

### ActionLink

用于非破坏性、低强调导航 / 管理入口。

```text
states:
  default / hover / focus-visible / disabled
hover:
  background or color change; no underline by default
disabled:
  prefer a button element when the action can be unavailable
anchor disabled fallback:
  aria-disabled="true" + tabindex="-1"; activation is prevented; hover background is not retained
forbidden:
  separate underline style per page
```

### Chip / Badge

- Chip 是可操作筛选或 removable tag：default / hover / focus-visible / pressed / disabled / removable。
- Badge 是状态 / 计数 / 元信息，不可操作：default / tone / outline / long-text。
- Chip 与 Badge 不得混用；长文本必须截断或换行，不得撑破容器。

### Card

```text
variants:
  task card / KPI / panel
states:
  default / hover / focus-visible / selected / dragging / loading / empty
rules:
  padding and radius from tokens
  hover does not shift bounding box
  focus ring remains visible at container edge
  long title and metadata have min-width: 0 defenses
```

### Overlay

- Modal 与 Drawer 共享 focus trap、focus restore、Esc、scrim、滚动约束。
- Footer 按钮统一右对齐且同高。
- Drawer 内 dense controls；Modal 内 regular controls。
- Scrim 不遮挡焦点元素；关闭路径有可读名称。

### Toast

```text
tones:
  info / success / warn / error / undo
rules:
  error remains available until dismissed or explicitly retried
  stacks never cover primary controls
  close target has accessible name
  max stack count and overflow are explicit
```

### EmptyState / ErrorState

- EmptyState：图标 + 说明 + 一个下一步行动；不得只写“暂无数据”。
- ErrorState：人话原因、可执行恢复动作、必要错误码；不泄露堆栈或内部路径。
- 两者不改变周边布局高度超过可接受阈值。

### Skeleton

- Skeleton 形状对应最终内容结构，避免加载完成后明显跳动。
- 不添加无意义动画；respect `prefers-reduced-motion`。
- 与 Empty / Error 状态互斥且切换有稳定触发条件。

### Table / List row

- 宽屏 table 与窄屏 row 是同一数据的不同布局，不是两套语义。
- states：loading / empty / error / row hover / row focus / selected / long-content。
- 长文本、空值、标签和数字有独立防御；窄屏不逐字断行、不产生失控横向滚动。

## Layout patterns

| 区域 | 契约 |
|---|---|
| Topbar | 所有 action 同高；身份区与主按钮垂直居中 |
| Form | Field 网格统一 gap；footer action 同高 |
| Detail drawer | 属性区 dense controls；行内输入 + 按钮同高 |
| Sidebar | 管理入口统一 ActionLink 行为 |
| Board / List | 页面级 token；卡片内长文本与空态可防御 |
| Dashboard | KPI / 图表 spacing 与 focus 一致 |

## Evidence contract

每个关键页面至少保存：

- desktop light
- desktop dark
- 375px light
- 关键 state 截图（loading / empty / error / invalid 中与页面相关者）

DOM 断言：

- topbar action 高度一致
- detail attr controls 高度一致
- same control-row children 高度一致
- focus / hover 不造成布局跳动
- coarse pointer 下目标尺寸达标

## DOM assertion method

- Tool: Playwright as a development-only dependency; runtime remains zero third-party dependency.
- Test location: `tests/test_browser_contract.py`.
- Viewports: desktop `1440x900`, narrow `375x844`, and pointer-coarse emulation.
- Key assertions:
  - topbar action bounding heights are equal within `0.5px`;
  - detail attribute controls are equal within `0.5px`;
  - each `.control-row` input / select / button heights are equal within `0.5px`;
  - hover and focus-visible bounding boxes do not shift more than `0.5px`;
  - coarse-pointer interactive targets are at least the project touch token;
  - key pages have no uncontrolled horizontal overflow.
- If Playwright is unavailable, browser-contract tests fail closed in CI-like local validation; they are not silently skipped. Interactive verification may supplement tests but cannot replace them.
- Screenshots confirm visual rendering; DOM assertions are the automated discovery mechanism.

## CSS split and tooling

- `index.html` load order is fixed: `tokens.css` → `components.css` → `app.css`.
- `tests/test_static.py` and contrast tooling read the same explicit list; no tool continues to assume `app.css` is the only stylesheet.
- `tools/contrast_audit.py` accepts the token source file and keeps `docs/contrast-audit.md` reproducible.
- During migration, duplicate selectors are forbidden: a primitive's canonical rules live in `components.css`; page-specific overrides live in `app.css` only when they do not alter token-controlled size, state, or spacing.

## Inline layout migration

1. Inventory all `style` attributes generated by shipped JavaScript.
2. Ban new layout values in shipped JS: `display`, `align-items`, `justify-content`, `flex-direction`, `flex`, `gap`, `margin`, `padding`, `width`, `height`, `min-width`, `max-width`, `min-height`, `max-height`, `position`, `inset`, or `overflow`.
3. Add a static test allowlist only for genuinely dynamic values (for example a progress bar percentage); each allowlist entry names the reason.
4. Migrate control rows, form rows, modal footers, detail sections, sidebar actions, and list/card layouts first.
5. Completion requires no unallowlisted JS inline layout style; page-specific layout classes live in CSS.

## Migration

1. 新增 `static/css/tokens.css` 与 `static/css/components.css`，保留 `app.css` 承载页面布局，增量迁移；同步更新加载顺序与工具输入。
2. 完成 coverage 表 Slice 1：Button、IconButton、Input、Select、Textarea、Field、Checkbox、ActionLink。
3. 完成 coverage 表 Slice 2：Chip / Badge、Card、Overlay、Toast、EmptyState、ErrorState、Skeleton、Table / List row。
4. 完成 coverage 表 Slice 3 与页面模式：Topbar / Detail / Form / Sidebar / Dashboard / Board / List，并同步状态证据。
5. 每个 Slice 都执行对应 inline-layout 迁移和静态 allowlist 收缩；全量测试通过后才进入下一 Slice。
6. 不做一次性 CSS 全量重写；任何未迁移项只能作为显式剩余实现项记录，不得算作完成。
