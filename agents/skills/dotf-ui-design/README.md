# dotf-ui-design 使用文档（人类阅读）

> 本文档面向人：说明 dotf-ui-design 门卫 skill 的设计背景、用法与维护方式。
> 它**不随 sync 分发**（sync 只拷贝 `SKILL.md`），也**不应被 skill/模型引用加载**；agent 侧的全部行为约定以 `SKILL.md` 为准。

## 1. 为什么做门卫（背景与目标）

直接给 agent 装一堆第三方 UI 设计 skill 的问题：每份 description 都可能被自动匹配触发，常驻上下文膨胀，且可能一次加载多个大 SKILL.md。门卫方案把外部 skill 收拢成单一入口：

```
用户显式喊 dotf-ui-design
     ↓ 触发（仅此入口）
  dotf-ui-design（门卫，轻量常驻）
     ↓ 确认意图后按注册表路由
  Read 某一个 refer skill 的 SKILL.md → 按其指引执行 → 用完即弃
```

核心收益：日常写代码时零误触；一次只加载一个外部 skill，上下文可控；增删外部 skill 只改注册表/候选目录，单一入口自己掌控。

## 2. 触发方式

纯显式触发：在对话中明确说「用 dotf-ui-design」之类。description 已收窄，普通前端编码、样式微调不会自动加载它。

## 3. 三道门禁

| 门禁 | 机制 | 防什么 |
|------|------|--------|
| 门 1 · 收窄触发 | description 明写"仅显式点名时使用"，不含宽泛自动匹配词 | 日常编码时被自动加载 |
| 门 2 · 强制确认意图 | 触发后先让用户选意图（审查/改造/新设计/查推荐/套风格/内置准则）；用户未选前禁止 Read 任何 refer skill；路由不明确必须再问 | 门卫一次把大 skill 拖进上下文、猜错目标 |
| 门 3 · 一次一个 | 一次只 Read 一个 refer skill，任务结束即弃 | 多个大 SKILL.md 叠加爆上下文 |

## 4. refer skill 注册表：`.dotf-ui-design.md`

- 位置：**各前端项目根目录**（与 `.service-manager.md` 同模式），随项目走、可提交。
- 作用：记录本项目实际预装了哪些 refer skill 及其真实路径，是门卫的路由依据。
- 维护：预装新 skill 后把条目补进去；门卫在用户确认使用未登记 skill 时也会顺手补登（文件不存在则先征得同意再创建）。
- 条目字段：名称 / SKILL.md 路径 / 适用场景 / 来源仓库 / 审计日期 / 是否已加固。

模板：

```markdown
# dotf-ui-design — <项目名>

## Refer Skills

| 名称 | SKILL.md 路径 | 适用场景 | 来源 | 审计日期 | 已加固 |
|------|---------------|----------|------|----------|--------|
| web-design-guidelines | .claude/skills/web-design-guidelines/SKILL.md | 审查现有 UI | vercel-labs/agent-skills | 2026-08-09 | 是 |
```

## 5. 路由映射（意图 → 候选）

| 用户意图 | 首选候选 |
|----------|----------|
| 审查/检查现有 UI、可访问性审计 | `web-design-guidelines` |
| 翻新/改造已有项目 UI | `redesign-existing-projects` |
| 新页面/组件，通用设计 | `design-taste-frontend` |
| 查配色/字体/设计模式推荐 | `ui-ux-pro-max` |
| 指定极简/工业/高端等风格 | `minimalist-ui` / `industrial-brutalist-ui` / `high-end-visual-design` |
| 无匹配 / 项目未装任何 refer skill | SKILL.md 内置准则（兜底） |

## 6. 候选 refer skill 清单（已核实来源，2026-08）

预装流程（在目标前端项目里执行）：

```bash
# 1. 安全审计（skills-store 流程）
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
git clone --depth 1 <来源仓库 URL> "$AUDIT_DIR/src"
bash <dotfiles>/agents/skills/skills-store/scripts/audit-skill.sh "$AUDIT_DIR/src/<skill>"

# 2. 审计通过 → 项目级预装（-a 按项目使用的 agent 选择）
cd <前端项目>
npx skills add <owner/repo> -s <skill> -a <tool> -y

# 3. 清理 + 核对实际落盘路径
rm -rf "$AUDIT_DIR"
npx skills list

# 4. 把条目写入项目根 .dotf-ui-design.md
```

| skill | 来源 | 场景 |
|-------|------|------|
| `web-design-guidelines` | `vercel-labs/agent-skills`（Vercel 官方） | 对照 Web Interface Guidelines（100+ 规则，含 a11y/UX）审查 UI 代码，输出 `file:line` 报告；每次审查动态拉取最新指南 |
| `redesign-existing-projects` | `leonxlnx/taste-skill` | 改造已有项目：先审计布局/间距/层级/风格，再修复 |
| `design-taste-frontend` | `leonxlnx/taste-skill`（默认主 skill） | 通用前端设计，按布局变化/动效强度/信息密度推断设计语言，反"AI 模板味"；新项目默认首选 |
| `ui-ux-pro-max` | `nextlevelbuilder/ui-ux-pro-max-skill` | 本地设计数据库：84 风格 / 192 配色 / 74 字体搭配 / 98 UX 准则 / 16 GSAP 动效 / 25 图表，22 个技术栈；查配色、字体、模式推荐（该仓库亦推自家 CLI `uipro init --ai <platform>`） |
| `minimalist-ui` | `leonxlnx/taste-skill` | Notion/Linear 式现代极简，适合 SaaS、工具型产品、内容后台 |
| `industrial-brutalist-ui` | `leonxlnx/taste-skill` | 工业粗野主义：瑞士排版、硬边框、极端字号对比、无圆角 |
| `high-end-visual-design` | `leonxlnx/taste-skill` | 高端克制 premium 风：柔和对比、大量留白、字体质感，适合品牌/营销页 |

### 防误触加固（可选）

第三方 skill 自带宽泛 description，即使预装在项目里，也可能被 agent 独立自动触发（绕开门卫）。加固方式：预装后把该 skill 的 description 标注「由 dotf-ui-design 路由调用，不单独触发」，并在注册表「已加固」列记录。是否加固取决于 agent 端是否允许已装 skill 独立触发。

## 7. 内置准则（兜底）

项目未装任何 refer skill、或用户选择不外加载时，门卫回退到 SKILL.md 文末的内置准则：先读项目现状（token/组件库/已有页面模式）→ 一致性 / 美观度 / 易用性要点 → 8 项交付前自检清单。与项目现有规范冲突时以项目为准。

## 8. 维护方式

| 要做什么 | 改哪里 |
|----------|--------|
| 调整门卫行为（门禁、路由逻辑、内置准则、候选目录） | `agents/skills/dotf-ui-design/SKILL.md`，然后 `scripts/agents/sync.sh all` 分发 |
| 新增候选 refer skill | SKILL.md 的「候选 refer skill 目录」+ 本文档第 6 节，保持两处一致 |
| 在某个前端项目启用某 refer skill | 该项目内走第 6 节的审计+预装流程，登记到项目根 `.dotf-ui-design.md` |
| 查看门卫在各 agent 的落地情况 | `dotf agents -d` |

注意：SKILL.md 是唯一会被 sync 分发、被模型加载的文件，候选目录保持简洁；细节说明只放本文档。
