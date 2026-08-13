---
id: dotf-ui-design
name: dotf-ui-design
description: UI 设计门卫/路由器：按用户意图路由到本 skill 内置 references/ 下的设计类 refer skill（Read 按需加载），或回退内置设计准则。仅在用户显式点名（如"用 dotf-ui-design"）时使用；普通编码、样式微调等任务不要自动加载本 skill。
---

# dotf-ui-design（UI 设计门卫）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。界面文案语言与项目一致。

本 skill 是**路由器**，不直接堆设计知识。被显式触发后：确认意图 → Read 本 skill `references/` 下的某一个 refer skill 执行；没有合适的 refer skill 时回退到文末的内置准则。

refer skill 已放在本 skill 的 `references/` 下并随分发到位，**无需任何额外安装**。第三方上游快照一般不修改；first-party 策展（如 `solo-ui-design`）可随规范演进修订。它们不在 agent 的 skill 注册路径上（只是数据文件），不会被独立自动触发。

## 三道门禁（防误触、防上下文膨胀）

1. **门 1 · 收窄触发**：仅用户显式点名时使用。普通前端编码、组件编写、样式调整，不加载本 skill。
2. **门 2 · 强制确认意图**：触发后**第一步永远是确认用户要做什么**，给选项：
   - ① 审查/检查现有 UI（含可访问性）
   - ② 翻新/改造已有项目 UI
   - ③ 设计新页面/组件（通用）
   - ④ 查配色/字体/设计模式推荐
   - ⑤ 套特定视觉风格（极简/工业/高端/纸墨编辑感等）
   - ⑥ 不加载 refer skill，直接用内置准则自检
   **用户未明确选择前，禁止 Read 任何 refer skill。** 选择后若路由目标仍不明确（多个候选都沾边），**必须再问用户确认**，不猜。
3. **门 3 · 一次只加载一个**：确定目标后用 **Read** 读对应 SKILL.md，按其指引执行。除非用户明确要求组合，否则不同时加载多个。任务结束后不再持续引用其内容（用完即弃）。

## 路由表（意图 → refer skill）

路径相对本 SKILL.md 所在目录（如 `~/.kimi-code/skills/dotf-ui-design/`）。

| 用户意图 | refer skill | 路径 |
|----------|-------------|------|
| 审查/检查现有 UI、可访问性审计 | `web-design-guidelines`（Vercel Web Interface Guidelines，100+ 规则，`file:line` 报告） | `references/web-design-guidelines/SKILL.md` |
| 翻新/改造已有项目 UI | `redesign-existing-projects`（先审计布局/间距/层级/风格，再修复） | `references/redesign-existing-projects/SKILL.md` |
| 新页面/组件，通用设计（默认首选） | `design-taste-frontend`（布局变化/动效强度/信息密度三维度推断设计语言，反"AI 模板味"） | `references/design-taste-frontend/SKILL.md` |
| 查配色/字体/设计模式/图表推荐 | `ui-ux-pro-max`（本地数据库：84 风格 / 192 配色 / 74 字体搭配 / 98 UX 准则 / 16 GSAP 动效 / 25 图表，22 技术栈） | `references/ui-ux-pro-max/SKILL.md` |
| 极简风（Notion/Linear 式，SaaS/工具/后台） | `minimalist-ui` | `references/minimalist-ui/SKILL.md` |
| 工业粗野风（瑞士排版、硬边框、极端字号对比） | `industrial-brutalist-ui` | `references/industrial-brutalist-ui/SKILL.md` |
| 高端克制 premium 风（品牌/营销页） | `high-end-visual-design` | `references/high-end-visual-design/SKILL.md` |
| 纸墨编辑感（内容站/知识库/编辑器型产品，同构后台） | `solo-ui-design`（克制排版、单一强调色、分段壳层、图标操作语法） | `references/solo-ui-design/SKILL.md` |
| 无匹配 / 用户选择不外加载 | 内置准则（见文末，兜底） | — |

注意：`ui-ux-pro-max` 为上游快照（vendored），其数据库可能随上游更新而过期；以实际可用性为准。

## 项目记录：`.dotf-ui-design.md`（可选）

项目根的 `.dotf-ui-design.md` 是**给人和下次选型看的记录**，不是路由依据（路由表固定在上文）。用途：

1. 记录本项目用过哪些 refer skill、效果与偏好笔记（下次选型参考）；
2. 用户想备忘的 UI 设计相关信息；
3. 项目额外自装的 UI skill（如有，记路径与场景）。

文件**不存在时不主动创建**；用户要求，或某个 refer skill 在本项目首次成功使用后，征得同意再创建/补记。只记元信息与经验，不写密钥。

### 模板

```markdown
# dotf-ui-design — <项目名>

## 使用记录

| 日期 | refer skill | 用于 | 效果/笔记 |
|------|-------------|------|-----------|
| 2026-08-09 | design-taste-frontend | 新版落地页 | 风格符合预期；动效偏多，下次调低 |

## 项目额外自装 skill

| 名称 | 路径 | 场景 | 来源 |
|------|------|------|------|
```

## 内置准则（兜底）

用户选择不外加载、或路由表无匹配时，用以下准则直接指导 UI 工作。

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

- 不自动触发；一次只加载一个 refer skill；**不修改 references/ 下的第三方上游快照**（发现问题记录到 `.dotf-ui-design.md`，升级走重新 vendor 流程）。first-party 策展（`solo-ui-design`）除外，可按 `ORIGIN.md` 演进。
- 不引入项目没有的设计体系或组件库依赖，确有需要先征得用户同意。
- 与项目现有规范冲突时以项目为准并提示用户。
- 大改版（整站换肤、设计体系迁移）先出方案讨论再动手。
