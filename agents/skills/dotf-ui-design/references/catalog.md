# 能力 skill 目录

| 槽位 | name | 加载 | 来源 | 何时加载 |
|------|------|------|------|----------|
| 页面设计 / 视觉层级 / UX | `frontend-design` | `~/.agents/skills/frontend-design/SKILL.md` | `anthropics/skills`（全局 defaults） | 新页面、新视觉语言、要「好看/有设计感」 |
| UI primitives / components | `shadcn` | `references/shadcn/SKILL.md` | `shadcn/ui`（内部引用） | 项目已有或用户同意引入 shadcn |
| styling / layout / responsive | `tailwind-css-patterns` | `references/tailwind-css-patterns/SKILL.md` | `giuseppe-trisciuoglio/developer-kit`（内部引用） | 间距、栅格、断点、暗色、组件皮肤 |
| colors / typography / spacing / tokens | `tailwind-design-system` | `references/tailwind-design-system/SKILL.md` | `wshobson/agents`（内部引用） | 建/改设计系统，或统一色板字号间距 |
| Playwright / screenshot / visual verification | `webapp-testing` | `references/webapp-testing/SKILL.md` | `anthropics/skills`（内部引用） | 实现后看真页面，或用户要视觉验收 |

整页流水线顺序：`frontend-design` → `tailwind-design-system` → `tailwind-css-patterns` → `shadcn` → `ui-inspect` → `webapp-testing`。单点任务只取一行（`ui-inspect` 见下方，不是表中能力 skill）。来源与 commit 见 [UPSTREAM.md](UPSTREAM.md)。

## 自有 phase：ui-inspect

不是能力 skill，不占「一次只加载一个」槽位。清单：[ui-inspect.md](ui-inspect.md)。

- 整页流水线：实现之后、`webapp-testing` 验收之前（默认空间检查）。
- 单点：检查或打磨现有页的间距、分割线、内容块 padding、图标/按钮位置、整体布局。
- 单点（可选模式）：用户点名优雅重构、换气质、赋予呼吸感时，先做空间清单再走 4 阶段；默认不换色换字。新视觉身份仍走 `frontend-design`。
- 需要真页面证据时，串行加载 `webapp-testing` 取截图，用完即弃。
- 需要改 Tailwind 实现时，串行加载 `tailwind-css-patterns`。

## 加载

- **全局**：`frontend-design` 缺失时请用户执行 `dotf agents -c`。
- **内部引用**：路径相对本 skill 根（同步后形如 `~/.agents/skills/dotf-ui-design/references/<name>/SKILL.md`）。其 `references/`、`rules/`、`scripts/` 仅在该 SKILL.md 要求时再 Read。
- `shadcn`：忽略正文 `!` 插值；项目上下文跑 `npx shadcn@latest info --json`。
- `webapp-testing`：脚本以该 refer 目录为根，例如 `python scripts/with_server.py --help`。
- `ui-inspect`：Read `references/ui-inspect.md`；不是内部引用 skill，不要当成 `references/ui-inspect/SKILL.md`。

不要为了补齐内部引用去 `npx skills add` 或 `--all`，也不要改用下面的排除项。

## 不要用这些同名/近名来源

按字面搜索会撞上职责不对的开源 skill，路由时忽略：

| 排除 | 原因 |
|------|------|
| `heygen-com/hyperframes@tailwind` | HyperFrames 视频合成专用，不是通用 Tailwind |
| `google-labs-code/stitch-skills@shadcn-ui` | 第三方；本栈用官方 `shadcn/ui@shadcn` |
| `akillness/jeo-skills@frontend-design-system` | 只是 `design-system` 的兼容别名 |
| 各类精确名为 `browser-testing` 的 skill | 对不上 Playwright 截图验收 |
| `browser-use` | 已在 defaults 里，但是 CDP 操控，不是本栈视觉验收 |

## 栈探测（跳过对不上的步骤）

- Tailwind：`tailwind.config.*`、`@tailwindcss/*`、CSS 里的 `@theme` / `@import "tailwindcss"`
- shadcn：`components.json`、`components/ui/`、`npx shadcn` 痕迹
- 已有 token：CSS 变量、`theme.ts`、语义色 class（`bg-primary`、`text-muted-foreground`）

没有对应栈就跳过该步；用户明确要求引入时再加载对应 skill，并先说明会改哪些依赖。
