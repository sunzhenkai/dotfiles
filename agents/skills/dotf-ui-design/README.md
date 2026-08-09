# dotf-ui-design 使用文档（人类阅读）

> 本文档面向人：说明 dotf-ui-design 门卫 skill 的设计背景、用法与维护方式。
> 它**不随 sync 分发**（sync 只拷贝 `SKILL.md` 和 `references/`），也**不应被 skill/模型引用加载**；agent 侧的全部行为约定以 `SKILL.md` 为准。

## 1. 为什么做门卫（背景与目标）

直接给 agent 装一堆第三方 UI 设计 skill 的问题：每份 description 都可能被自动匹配触发，常驻上下文膨胀，且可能一次加载多个大 SKILL.md。门卫方案把外部 skill 收拢成单一入口：

```
用户显式喊 dotf-ui-design
     ↓ 触发（仅此入口）
  dotf-ui-design（门卫，轻量常驻）
     ↓ 确认意图后按路由表
  Read references/ 下某一个 refer skill → 按其指引执行 → 用完即弃
```

核心收益：日常写代码时零误触；一次只加载一个外部 skill，上下文可控；增删外部 skill 只改 vendor 内容与路由表，单一入口自己掌控。

## 2. 架构：vendored references，随 sync 分发

refer skill 已放进 `references/`，由 `scripts/agents/sync.py` 随 `SKILL.md` 一并分发到各 agent 环境（references 原样拷贝、字节一致）。因此：

- **无需逐项目安装**，各 agent 开箱即有；
- references 下的文件不在 agent 的 skill 注册路径上（如 `~/.kimi-code/skills/` 只认一级 `<name>/SKILL.md`），**不会独立触发**，门禁没有逃逸口；
- 第三方上游快照一般不修改；发现问题记录到项目 `.dotf-ui-design.md`，升级走重新 vendor 流程（见第 6 节）。first-party 策展（`solo-ui-design`）可直接修订，见其 `ORIGIN.md`。

## 3. 触发方式

纯显式触发：在对话中明确说「用 dotf-ui-design」之类。description 已收窄，普通前端编码、样式微调不会自动加载它。

## 4. 三道门禁

| 门禁 | 机制 | 防什么 |
|------|------|--------|
| 门 1 · 收窄触发 | description 明写"仅显式点名时使用"，不含宽泛自动匹配词 | 日常编码时被自动加载 |
| 门 2 · 强制确认意图 | 触发后先让用户选意图（审查/改造/新设计/查推荐/套风格/内置准则）；用户未选前禁止 Read 任何 refer skill；路由不明确必须再问 | 门卫一次把大 skill 拖进上下文、猜错目标 |
| 门 3 · 一次一个 | 一次只 Read 一个 refer skill，任务结束即弃 | 多个大 SKILL.md 叠加爆上下文 |

## 5. refer skill 清单（2026-08）

| references/ 目录 | 场景 | 来源 |
|------------------|------|------|
| `web-design-guidelines` | 审查/检查现有 UI、a11y 审计：对照 Vercel Web Interface Guidelines（100+ 规则）输出 `file:line` 报告，每次审查动态拉取最新指南 | 上游 vendor：`vercel-labs/agent-skills` |
| `redesign-existing-projects` | 翻新/改造已有项目 UI：先审计布局/间距/层级/风格，再修复 | 上游 vendor：`leonxlnx/taste-skill`（`skills/redesign-skill`） |
| `design-taste-frontend` | 新页面/组件通用设计（默认首选）：布局变化/动效强度/信息密度三维度推断设计语言，反"AI 模板味" | 上游 vendor：`leonxlnx/taste-skill`（`skills/taste-skill`） |
| `ui-ux-pro-max` | 查配色/字体/设计模式/图表推荐：本地数据库 84 风格 / 192 配色 / 74 字体搭配 / 98 UX 准则 / 16 GSAP 动效 / 25 图表，22 技术栈（~1.8M，44 文件） | 上游 vendor：`nextlevelbuilder/ui-ux-pro-max-skill` |
| `minimalist-ui` | 极简风（Notion/Linear 式），SaaS/工具型产品/内容后台 | 上游 vendor：`leonxlnx/taste-skill`（`skills/minimalist-skill`） |
| `industrial-brutalist-ui` | 工业粗野风：瑞士排版、硬边框、极端字号对比、无圆角 | 上游 vendor：`leonxlnx/taste-skill`（`skills/brutalist-skill`） |
| `high-end-visual-design` | 高端克制 premium 风：柔和对比、大量留白、字体质感，品牌/营销页 | 上游 vendor：`leonxlnx/taste-skill`（`skills/soft-skill`） |
| `solo-ui-design` | 纸墨编辑感：内容站/知识库/编辑器型产品及其同构后台；克制排版、单一强调色、分段壳层、图标操作语法 | **first-party**：提炼自 `solo-blog` `.agents/skills/ui-design/`（见其 `ORIGIN.md`） |

第三方快照的上游 commit 与 vendor 日期见 `references/UPSTREAM.md`。

注意：`ui-ux-pro-max` 上游已转向自家 CLI（`uipro init`）生成模式；vendor 的是其 `.claude/skills/` 自包含快照（含 data/ CSV，不依赖 CLI），但内容可能随上游更新过期。

## 6. 升级 / 新增 refer skill（重新 vendor 流程）

```bash
# 1. 浅克隆上游到临时目录
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
git clone --depth 1 <上游仓库 URL> "$AUDIT_DIR/src"

# 2. 安全审计（critical 阻断则不要 vendor）
bash <dotfiles>/agents/skills/skills-store/scripts/audit-skill.sh "$AUDIT_DIR/src/<skill 目录>"

# 3. 原样覆盖 references/<name>/（不修改内容）
rm -rf agents/skills/dotf-ui-design/references/<name>
cp -a "$AUDIT_DIR/src/<skill 目录>" agents/skills/dotf-ui-design/references/<name>

# 4. 更新 references/UPSTREAM.md 的 commit 与日期，清理临时目录
rm -rf "$AUDIT_DIR"

# 5. 分发
scripts/agents/sync.sh all
```

新增 skill 同理，另需：在 `SKILL.md` 路由表加一行 + 本文档第 5 节加一行，保持两处一致。

## 7. 项目记录：`.dotf-ui-design.md`（可选）

项目根的 `.dotf-ui-design.md` 是**选型参考 + 用户信息记录**，不是路由依据：

1. 记录本项目用过哪些 refer skill、效果与偏好笔记（下次选型参考）；
2. 用户想备忘的 UI 设计相关信息；
3. 项目额外自装的 UI skill（如有）。

文件不存在时不主动创建；用户要求，或某 refer skill 首次成功使用后征得同意再建。模板见 SKILL.md。

## 8. 内置准则（兜底）

用户选择不外加载、或路由表无匹配时，门卫回退到 SKILL.md 文末的内置准则：先读项目现状（token/组件库/已有页面模式）→ 一致性 / 美观度 / 易用性要点 → 8 项交付前自检清单。与项目现有规范冲突时以项目为准。

## 9. 维护方式

| 要做什么 | 改哪里 |
|----------|--------|
| 调整门卫行为（门禁、路由、内置准则） | `agents/skills/dotf-ui-design/SKILL.md`，然后 `scripts/agents/sync.sh all` |
| 升级/新增/移除第三方 refer skill | 第 6 节的 vendor 流程 + SKILL.md 路由表 + 本文档第 5 节 |
| 修订纸墨编辑感规范 | 直接改 `references/solo-ui-design/`（见其 `ORIGIN.md`）+ 必要时同步路由表说明，再 `scripts/agents/sync.sh all` |
| 记录项目使用经验 | 项目根 `.dotf-ui-design.md`（可选） |
| 查看分发情况 | `dotf agents -d` |

注意：SKILL.md 与 references/ 会被 sync 分发并可能被模型加载；细节说明只放本文档。
