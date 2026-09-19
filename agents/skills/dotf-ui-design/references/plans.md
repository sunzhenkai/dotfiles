# 计划落盘与闭环

audit 与 motion 模式的产出是计划，执行交给任意 agent（包括更便宜的模型）。本文件定义落盘格式、状态生命周期、执行承接与 reconcile，是三模式共用的闭环协议。

## 落盘

- 目录 `design-plans/`（该目录已存在且另有用途时改用 `ui-design-plans/`）。命名 `NNN-short-slug.md`，编号单调递增，尊重已有计划。
- audit 模式用 improve-ui 的 plan-template，motion 模式用 improve-animations 的 PLAN-TEMPLATE；两模板的公共要求都要满足：自包含、内联精确值、带验证（含 feel check）与停止条件。
- 计划必须自包含：执行者没有本次对话上下文，也没有品味。禁止"用上面讨论的缓动"这类引用；内联精确值——cubic-bezier、时长、file:line、现码原文。
- 每份计划盖 commit 戳：Git 仓库内取 `git rev-parse --short HEAD`；不在 Git 仓库或命令失败时写 `unavailable` 并记录日期。

## 状态机与台账

计划状态：`TODO → IN_PROGRESS → DONE / BLOCKED / RETIRED`。

维护 `design-plans/README.md` 作为台账，列：

| 列 | 说明 |
| --- | --- |
| 编号 / 标题 | 与计划文件对应 |
| 模式 | audit 或 motion |
| Priority | P0 / P1 / P2，推导见下 |
| 状态 | 状态机值 |
| 验证回执 | 执行后填写：机械检查与 feel check 结果、执行者、日期 |
| 顺序 / 依赖 | 建议执行顺序与计划间依赖 |

Priority 推导：

- motion：severity 直接映射 HIGH → P0、MEDIUM → P1、LOW → P2。
- audit：confidence 与影响联合推导——高置信且阻断主任务流程 → P0；高置信但影响局部 → P1；其余 → P2。在计划文件内记录推导依据。

## 执行承接

- 被要求执行某份计划时可以承接（本 skill 或任何其他 agent），但**以计划文本为唯一规格**；执行者不享有审计时的对话上下文。
- 执行者发现现场与 commit 戳或计划引用不符时：停下报告，不即兴发挥；回到 reconcile。
- 执行完成后先过验证再置状态：机械检查（typecheck / lint / build，以计划内命令为准）+ 计划内的 feel check；全部通过才标 DONE，验证未过标 BLOCKED 并写明原因。
- feel check 的现场取证按 [visual-evidence.md](visual-evidence.md)；独立验收走 [review.md](review.md) 阶段，其 verdict 报告作为回执附件引用。
- 回执写入 `design-plans/README.md`，不改写计划原文。

## Reconcile（闭环）

被要求 `reconcile` 时，对照当前代码重查既有计划：

- 已落地且验证通过 → 标 DONE。
- file:line 过期但问题仍在 → 刷新引用与 commit 戳。
- 问题已消失（被其他改动修复）→ 标 RETIRED。
- 验证未过或现场已漂移 → 不标 DONE；把偏差作为新候选**回流 audit / motion 模式重新取证**，不改计划凑现场。

design 模式的产出被 audit 验收时，发现的偏差同样走本协议落计划，形成 design → audit → plans → execute → reconcile 的完整闭环。
