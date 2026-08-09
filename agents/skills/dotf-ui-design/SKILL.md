---
id: dotf-ui-design
name: dotf-ui-design
description: UI 设计门卫/路由器：按用户意图路由到项目预装的设计类 refer skill（Read 按需加载），或回退内置设计准则。仅在用户显式点名（如"用 dotf-ui-design"）时使用；普通编码、样式微调等任务不要自动加载本 skill。
---

# dotf-ui-design（UI 设计门卫）

本 skill 是**路由器**，不直接堆设计知识。被显式触发后：确认意图 → 查项目注册表 → Read 一个 refer skill 执行；没有合适的 refer skill 时回退到文末的内置准则。

## 三道门禁（防误触、防上下文膨胀）

1. **门 1 · 收窄触发**：仅用户显式点名时使用。普通前端编码、组件编写、样式调整，不加载本 skill。
2. **门 2 · 强制确认意图**：触发后**第一步永远是确认用户要做什么**，给选项：
   - ① 审查/检查现有 UI（含可访问性）
   - ② 翻新/改造已有项目 UI
   - ③ 设计新页面/组件（通用）
   - ④ 查配色/字体/设计模式推荐
   - ⑤ 套特定视觉风格（极简/工业/高端等）
   - ⑥ 不加载外部 skill，直接用内置准则自检
   **用户未明确选择前，禁止 Read 任何 refer skill。** 选择后若路由目标仍不明确（多个候选都沾边、注册表缺路径、候选未安装），**必须再问用户确认**，不猜。
3. **门 3 · 一次只加载一个**：确定目标后用 **Read** 读对应 SKILL.md，按其指引执行。除非用户明确要求组合，否则不同时加载多个。任务结束后不再持续引用其内容（用完即弃）。

## 第 1 步：读注册表 `.dotf-ui-design.md`

refer skill 随各前端项目预装，注册表按项目维护，位于**项目根**（与 `.service-manager.md` 同模式）。

- 触发后先读项目根 `.dotf-ui-design.md`（若存在），从中拿路由表：每个条目含 名称 / SKILL.md 实际路径 / 适用场景 / 来源仓库 / 审计日期 / 是否已加固 description。
- 文件不存在或匹配不明确 → 向用户确认下一步（装候选 / 用内置准则 / 其他）。
- 用户确认使用某个尚未登记的 refer skill 时，顺手把条目补进注册表；文件不存在则**先征得同意再创建**。
- 注册表只记元信息，不写密钥。

### 注册表模板

```markdown
# dotf-ui-design — <项目名>

## Refer Skills

| 名称 | SKILL.md 路径 | 适用场景 | 来源 | 审计日期 | 已加固 |
|------|---------------|----------|------|----------|--------|
| web-design-guidelines | .claude/skills/web-design-guidelines/SKILL.md | 审查现有 UI | vercel-labs/agent-skills | 2026-08-09 | 是 |
```

## 第 2 步：路由（意图 → 候选 refer skill）

| 用户意图 | 首选候选 |
|----------|----------|
| 审查/检查现有 UI、可访问性审计 | `web-design-guidelines` |
| 翻新/改造已有项目 UI | `redesign-existing-projects` |
| 新页面/组件，通用设计 | `design-taste-frontend` |
| 查配色/字体/设计模式推荐 | `ui-ux-pro-max` |
| 指定极简/工业/高端等风格 | `minimalist-ui` / `industrial-brutalist-ui` / `high-end-visual-design` |
| 无匹配 / 项目未装任何 refer skill | 内置准则（见文末，兜底） |

## 候选 refer skill 目录（已知来源，需审计后预装）

预装一律先走 skills-store 的安全审计流程（临时目录 clone + `audit-skill.sh`），通过后在**目标前端项目**里 `npx skills add`（`-a <tool>` 按项目使用的 agent 选择，决定落盘到 `.claude/skills/`、`.zcode/skills/` 等），装完用 `npx skills list` 核对实际路径并写入注册表。门卫只引用，不负责安装。

### A. 审查 / 改造现有 UI

| skill | 来源 | 场景 | 安装 |
|-------|------|------|------|
| `web-design-guidelines` | `vercel-labs/agent-skills`（Vercel 官方） | 对照 Web Interface Guidelines（100+ 规则，含 a11y/UX）审查 UI 代码，输出 `file:line` 报告；每次审查动态拉取最新指南 | `npx skills add vercel-labs/agent-skills -s web-design-guidelines -a <tool> -y` |
| `redesign-existing-projects` | `leonxlnx/taste-skill` | 改造已有项目：先审计布局/间距/层级/风格问题，再修复 | `npx skills add leonxlnx/taste-skill -s redesign-existing-projects -a <tool> -y` |

### B. 新界面设计（通用 / 设计决策推荐）

| skill | 来源 | 场景 | 安装 |
|-------|------|------|------|
| `design-taste-frontend` | `leonxlnx/taste-skill`（默认主 skill） | 通用前端设计，按布局变化/动效强度/信息密度推断设计语言，反"AI 模板味"；新项目默认首选 | `npx skills add leonxlnx/taste-skill -s design-taste-frontend -a <tool> -y` |
| `ui-ux-pro-max` | `nextlevelbuilder/ui-ux-pro-max-skill` | 本地设计数据库：84 风格 / 192 配色 / 74 字体搭配 / 98 UX 准则 / 16 GSAP 动效 / 25 图表，覆盖 22 个技术栈；查配色、字体、模式推荐 | `npx skills add nextlevelbuilder/ui-ux-pro-max-skill -a <tool> -y`（该仓库亦推自家 CLI `uipro init --ai <platform>`） |

### C. 特定视觉风格

| skill | 来源 | 场景 | 安装 |
|-------|------|------|------|
| `minimalist-ui` | `leonxlnx/taste-skill` | Notion/Linear 式现代极简，适合 SaaS、工具型产品、内容后台 | `npx skills add leonxlnx/taste-skill -s minimalist-ui -a <tool> -y` |
| `industrial-brutalist-ui` | `leonxlnx/taste-skill` | 工业粗野主义：瑞士排版、硬边框、极端字号对比、无圆角 | `npx skills add leonxlnx/taste-skill -s industrial-brutalist-ui -a <tool> -y` |
| `high-end-visual-design` | `leonxlnx/taste-skill` | 高端克制 premium 风：柔和对比、大量留白、字体质感，适合品牌/营销页 | `npx skills add leonxlnx/taste-skill -s high-end-visual-design -a <tool> -y` |

**防误触加固（可选）**：第三方 skill 自带宽泛 description，可能被 agent 独立自动触发。预装后可将其 description 标注「由 dotf-ui-design 路由调用，不单独触发」，并在注册表「已加固」列记录。

## 内置准则（兜底）

项目没有合适 refer skill、或用户选择不外加载时，用以下准则直接指导 UI 工作。

### 第 0 步：先读项目现状

动手前先找项目已有的设计基线，**沿用而不是另起炉灶**：设计 token / 主题变量（CSS variables、`theme.ts`、`tailwind.config.*`）、已用的组件库（Tailwind/MUI/Ant Design/shadcn 等）、已有同类页面的结构间距配色模式。项目规范与本准则冲突时以项目为准，并向用户说明。

### 一致性

- 复用优先：优先用现有组件与 token，不造平行实现。
- 间距成体系：4px 基数刻度（4/8/12/16/24/32），不写魔法数字。
- 字号阶梯克制：一个页面 3–4 级字号，层级靠字重和颜色辅助。
- 颜色有语义：primary/danger/success/muted 固定含义，同一含义不用两种颜色。
- 交互模式统一：相同操作（删除、提交、跳转）用相同控件与反馈。

### 美观度

- 视觉层级靠对比（大小、字重、深浅）；次要信息降噪。
- 留白舍得给：相关靠近、无关拉开（邻近性原则）。
- 对齐：同列元素边缘对齐，避免 1–2px 的"差不多对齐"。
- 排版：正文行长 45–75 字符，行高约 1.5–1.7。
- 配色受限：主色 ≤ 2，正文对比度 ≥ 4.5:1。
- 装饰克制：阴影/圆角/动画统一而少；动画服务于反馈，时长 150–300ms。

### 易用性

- 交互状态齐全：hover/focus/active/disabled + loading/empty/error，写组件时逐个检查。
- 表单：每个输入有可见 label；错误提示可行动（哪里错、怎么改）；提交中防重复提交；危险操作需确认或可撤销。
- a11y 基线：语义化标签（不用 div+onClick 冒充按钮）、键盘可达、焦点可见、图标按钮有 aria-label、颜色不作为唯一信息载体。
- 响应式：窄屏不溢出，触控目标 ≥ 44px。
- 文案：按钮用动词开头，语言与项目一致。

### 交付前自检清单

- [ ] 沿用了项目已有 token/组件/模式，无平行实现
- [ ] 间距、字号取自既有刻度，无魔法数字
- [ ] 颜色全部来自语义色板，对比度达标
- [ ] hover/focus/disabled/loading/empty/error 状态齐全
- [ ] 表单有 label，错误提示可行动，提交防重复
- [ ] 键盘可操作、焦点可见、图标按钮有 aria-label
- [ ] 窄屏/移动端不溢出，触控目标够大
- [ ] 新页面与已有页面视觉风格一致

## 边界

- 不自动触发；一次只加载一个 refer skill；不篡改第三方 skill 内容。
- 不引入项目没有的设计体系或组件库依赖，确有需要先征得用户同意。
- 与项目现有规范冲突时以项目为准并提示用户。
- 大改版（整站换肤、设计体系迁移）先出方案讨论再动手。
