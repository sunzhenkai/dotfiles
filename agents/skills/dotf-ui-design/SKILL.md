---
id: dotf-ui-design
name: dotf-ui-design
description: UI Engineering 路由器：按意图编排 frontend-design（视觉/UX）、shadcn（组件）、tailwind-css-patterns（样式/布局）、tailwind-design-system（tokens）、webapp-testing（Playwright 截图验收），并含自有 ui-inspect phase（现有页间距/布局/padding 等细节检查，可选优雅重构）。用于用户点名 dotf-ui-design / UI Engineering，或明确要设计/翻新页面、落地设计系统、用 shadcn+Tailwind 做 UI、做浏览器视觉验收、检查/打磨现有页细节、或对现有页做优雅重构时。普通改样式、写组件、pretty-view-html/ppt 不要自动加载。
---

# dotf-ui-design（UI Engineering 路由器）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。界面文案语言与项目一致。

本 skill 是**薄路由器**，不堆设计知识。被触发后：确认意图 → 按 [catalog](references/catalog.md) 选一条能力 skill → Read 其 `SKILL.md` 并按其执行。现有页空间/对齐细节走自有 phase [ui-inspect](references/ui-inspect.md)，不是第五条能力 skill。对现有页的优雅重构也走该 phase 的可选模式，不要改道去堆一套新视觉体系。

```text
UI Engineering
├── frontend-design           页面设计 / 视觉层级 / UX     （全局 defaults）
├── shadcn                    UI primitives / components   （内部引用）
├── tailwind-css-patterns     styling / layout / responsive（内部引用）
├── tailwind-design-system    colors / typography / tokens （内部引用）
├── webapp-testing            Playwright / screenshot      （内部引用）
└── ui-inspect                现有页空间细节 / 可选优雅重构 （自有 phase）
```

`frontend-design` 由 `agents/skills-defaults.yaml` 装到 `~/.agents/skills/`。其余 4 条在本 skill 的 `references/` 下，随分发到位，**不是**独立 skill，不要再 `npx skills add` 到全局。`ui-inspect` 清单在 `references/ui-inspect.md`，不要当成独立 skill 安装。

## 三道门禁

1. **门 1 · 收窄触发**：用户点名本 skill /「UI Engineering」，或明确要设计/翻新页面、建立或审计设计 token、用 shadcn + Tailwind 落地 UI、用 Playwright 做视觉验收，检查/打磨现有页的间距、分割线、padding、图标按钮位置、整体布局等细节，或对现有页做优雅重构/换气质。不算触发：普通改 class、补组件、修 bug；`pretty-view-html` / `pretty-view-ppt`；闲聊「什么是 shadcn」。新页面或新视觉身份走 `frontend-design`，不要当成 ui-inspect 默认检查。
2. **门 2 · 先看项目再选路**：动手前先找已有 token / 主题、组件库、同类页面。项目没有 shadcn 或 Tailwind 时，不要为了走某条路由而引入；确需引入先征得同意。意图不清或候选多于一条时先问，不猜。
3. **门 3 · 一次只加载一个能力 skill**：按 catalog 用 Read 读对应 `SKILL.md`。整页流水线按顺序**串行**加载，用完即弃；禁止一次读进多个上游正文。`ui-inspect` 不是能力 skill，不占本槽。`browser-use` 不在本栈。

## 执行流程

1. 过门禁；对照 catalog 选定 skill，或进入 `ui-inspect`。整页新建或翻新默认顺序：

   ```text
   项目基线 → frontend-design → tailwind-design-system
   → tailwind-css-patterns → shadcn → 实现 → ui-inspect → webapp-testing
   ```

   单点任务只走对应一条（例如「加 Dialog」→ `shadcn`，「截图看看」→ `webapp-testing`，「检查页面间距」→ `ui-inspect`，「优雅重构现有页」→ `ui-inspect` 可选模式）。项目栈对不上的步骤跳过。
2. `frontend-design` 的 `SKILL.md` 不存在 → 请用户跑 `dotf agents -c`。内部引用缺失视为本 skill 损坏，不要改用 catalog 排除的同名第三方，也不要自行 `npx skills add --all`。
3. 严格按该能力 skill 执行。`shadcn` 正文里的 `!` 插值可忽略，需要项目上下文时自己跑 `npx shadcn@latest info --json`。`webapp-testing` 的脚本以 `references/webapp-testing/` 为根。`ui-inspect` 按 [ui-inspect.md](references/ui-inspect.md) 执行：未点名优雅重构则只做空间检查；点名了先清单再走 4 阶段。需要截图时串行加载 `webapp-testing`，需要改间距实现时串行加载 `tailwind-css-patterns`，用完即弃。与项目规范冲突时以项目为准并说明。
4. 大改版（整站换肤、换组件库、重建 token）先出方案再动手。

## 项目记录（可选）

项目根 `.dotf-ui-design.md` 给人和下次选型看，**不是**路由依据。文件不存在时不主动创建；用户要求，或某条能力 skill 在本项目首次用顺后征得同意再记。只记元信息与经验，不写密钥。

```markdown
# dotf-ui-design — <项目名>

## 使用记录

| 日期 | skill | 用于 | 效果/笔记 |
|------|-------|------|-----------|
| 2026-08-28 | frontend-design | 新落地页 | 方向可用；动效偏多 |

## 项目栈

- tokens:
- components:
- styling:
```

## 内置准则（兜底）

用户明确不加载上游、或 `frontend-design` 未安装仍要继续时，用下面几条直接做，不再编一套平行设计体系。

- 复用现有组件与 token，不造平行实现；间距走项目刻度，没有则用 4px 基数。
- 一页 3–4 级字号；颜色有语义且对比度达标；主色 ≤ 2。
- hover / focus / active / disabled / loading / empty / error 写组件时逐个检查。
- 语义化控件、键盘可达、焦点可见、图标按钮有可访问名字；窄屏不溢出，触控目标够大。
- 交付前确认：无平行实现、无魔法数字、状态齐全、与已有页面同一套视觉语言；整页或打磨任务对照 `ui-inspect` 清单过一遍空间细节。

## 边界

- 不修改 `references/` 下的第三方快照；`ui-inspect.md` 是本 skill 自有清单，可随本协议更新。发现问题记到 `.dotf-ui-design.md`，升级改 [UPSTREAM.md](references/UPSTREAM.md) 后重新 vendor。
- 这 4 条内部引用不要装进 `~/.agents/skills/<name>/`，也不要写进 `skills-defaults.yaml`。
- 不拦截 `pretty-view-html` / `pretty-view-ppt`；它们有自己的设计路径。
- 不把 CDP 操控（`browser-use`）当成视觉验收。
- `frontend-design` 与共享目录不一致时，以 `~/.agents/skills/frontend-design/SKILL.md` 为准，并提示跑 `dotf agents -c`。
