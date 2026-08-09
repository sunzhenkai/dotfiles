# 起源与同步说明

本目录是 **first-party 策展**（非第三方 vendor 快照），可随 Solo UI 规范演进主动修订。

## 来源

提炼自 `solo-blog`（定风坡）仓库的 `.agents/skills/ui-design/`：

- 执行层：`SKILL.md` → 本目录 `SKILL.md`（去掉项目路由、i18n 实现、知识库 INDEX/CHANGELOG、Radix 迁移仪式等特例）
- 设计语言：`DESIGN_LANGUAGE.md` → 本目录 `DESIGN_LANGUAGE.md`（保留原则与推荐约定，去掉站名文案、具体组件路径、localStorage key 等）

## 已迁入的上游补充（按需）

仅迁入支撑 Design / Optimize / Audit 模式的通用原文：

| 路径 | 用途 |
| --- | --- |
| `references/frontend-design/` | Design 模式补充 |
| `references/baseline-ui/` | Optimize 模式补充 |
| `references/improve-ui/` | Audit 模式补充（含 plan-template） |

## 有意未迁入

| 原内容 | 原因 |
| --- | --- |
| `references/upstream/shadcn/` | 栈实现手册，体积大；Compose 改查项目/官方文档 |
| `references/upstream/migrate-radix-to-base/` | 一次性迁移手册，非设计原则 |
| `references/upstream/ui-skills-root/` | 历史多 skill 路由，与门卫职责重叠 |
| `CHANGELOG.md` / `INDEX.md` / `design-plans/` | 项目踩坑知识库，不可复用 |
| `references/conflicts.md` | 项目层裁决，已吸收进本目录 SKILL 冲突序 |

## 回写建议

若在通用项目中验证出可泛化的新原则，优先更新本目录；仅当结论依赖定风坡路由/组件/文案时，再回写 `solo-blog` 的 `ui-design`。
