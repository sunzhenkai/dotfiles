# 复杂档 Goal 引入质量画像门与固定三角色审阅

- target: agents/skills/task-wizard
- mode: update
- patch: 20260927-003054-quality-profile-gate
- risk: medium
- status: proposed

## Intent

复杂产品交付常被写成布尔功能项：每个功能动词都有实现路径，但页面、交互状态、数据并发与角色底线缺失，交付结果退化成 demo。要让 task-wizard 的复杂档 Goal 在进入实现前，被一份可检查的质量画像和 product / design / engineer 三角色审阅约束住。

要改变的行为：

1. 新增 `references/quality-profile.md`，写通用画像契约：固定字段（受众与场景、规模与运行假设、页面/主流程、角色底线 product/design/engineer、显式降级），主流程 3-7 条，降级每条写「维度 / 默认期望 / 实际选择 / 原因 / 确认状态」，`pending` 只能由用户改 `confirmed`。
2. 复杂档判定补充产品交付硬指标（多主页面、两个以上生效角色或权限边界、跨请求或跨用户复用的持久化数据、外部集成/实时协作/通知/审计、项目级重构或业务逻辑复杂且涉及面广）；命中即复杂，不得降档绕过质量门；单页原型与无持久化静态演示不触发。
3. Goal 方案模板在「完成判据」后加「质量画像（复杂档必填）」小节，缺必要字段判 P0，路由 `完善中：补质量画像并再审`，不开工；确实写不出才走「理解不够」。
4. 质量画像与显式降级进入审阅边界与派审提示词；复杂档初审与执行中新决策点固定委托 `role-based-reviewer mode=review roles=product,design,engineer`，Blocker→P0、Major→P1、Minor→P2，读不到该 skill 走退出点「审阅派不出」。
5. 完成门要求字段齐全且 `pending` 降级为 0，`confirmed` 降级在验证记录可追踪；复杂档交接 task-explore 时逐字带画像原文快照。
6. 新增退出点「降级未确认」承载 pending 门禁（不开工、不交接）。

非目标：不改状态机与 P0/P1 核对循环；不改简单、中等两档行为；不引入自动质量评分器；不改 task-explore 生命周期与 taskflow 编排协议（画像快照的下游登记属后续 patch）；不同步 `openspec/specs/task-wizard-goal/spec.md`（另轮处理）。

## Conflict check

- 与 role-based-reviewer 门 1 不冲突：它要求显式触发，本改动把复杂档 Goal 工作流成为正当调用方并固定 `roles`，属用户显式指定的角色集；其门 3 默认只报 Blocker/Major，故 Minor→P2 在多数情况下为空，不改变 P 级核对语义。
- 与「其余情况」默认人选分支并存：新分支只对复杂档生效，且用户在 goal 原文或当轮消息点名其他审阅方式时以点名为准，不叠加，避免与 `agent-roster` 分支互相抢派审。
- 与「审阅不审架构、接口、schema、代码骨架」不冲突：画像字段停在页面、主流程、状态与底线层面，reference 明确画像不引入新审阅对象。
- 与既有「交付标准」有重叠风险，用分工条款消除：复杂档把验证或测试覆盖、错误与边界行为、运行假设收进画像，「交付标准」只写画像未覆盖项，避免双清单。
- pending 降级若同时按 P1 与退出点处理会有两套门禁，故只走退出点「降级未确认」，不改 P1 定义；ADR 里「缺确认的降级视为 P1」按此收敛为更强的停等语义。
- 「完善中」路由前缀已被「纪律」识别为只改方案不改代码，新路由 `完善中：补质量画像并再审` 复用该机制，不新增状态。
- 简单/中等档不受影响：模板该小节写「无」，完成门与派审人选均按档位分流。none 其余。

## Rationale

「功能存在」不等于可交付，质量要满足干系人显式与隐含需求；把这类隐含需求压成一份固定字段契约，是让审阅者能逐条判定、而不是接受「高质量」这类形容词的最小结构。固定三角色给出产品、UI、工程三个视角的早期发现，输出仍映射进既有 P0/P1/P2 核对循环，因此不需要新评分器也不改状态机。降级确认独立于审阅授权，避免 agent 单方面放弃约束后仍算收敛。规则全程用通用措辞与占位字段，不含任何专有页面名、主机路径或项目名，可随 skill 分发。可验证点：字段齐全性、每条底线的验证方式、pending 计数、交接快照是否逐字，均为可机械检查的话。

## Files

- `agents/skills/task-wizard/references/quality-profile.md`（新增）— 固定字段契约、与交付标准分工、降级确认规则、缺字段判级、交接快照与完成门
- `agents/skills/task-wizard/SKILL.md` — 复杂度路由补产品交付硬指标与画像快照交接句；Goal 方案正文说明与模板新增小节、交付标准措辞、退出点清单；审阅节补审阅边界、派审提示词、复杂档固定三角色人选分支、P0 定义；写完之后复杂档路由句带画像快照；退出点判定新增「降级未确认」；做完补复杂档完成门

## Validation

- 应用前：`git apply --check --recount agents/skills/task-wizard/patches/20260927-003054-quality-profile-gate/change.patch`（仓库根执行）。
- 应用后：`git diff --check -- agents/skills/task-wizard`；核对实际 diff 与本 proposal 一致；`SKILL.md` frontmatter 合法且 `name` 与目录名一致；`references/quality-profile.md` 链接可达；grep 确认无专有项目名、个人主机路径、内部 URL 等不可分发内容；未触历史 `patches/`。
- 行为核对（人工读方案）：简单/中等档模板该小节写「无」且不强制三角色；复杂档缺画像字段路由以「完善中」开头、不进入实现；状态集合仍为 `执行中 / 已停 / 已交接 / 已完成`；核对循环段落无改动。
- 本 patch 不自动应用、不 sync、不 commit；应用需按 medium 门禁取得用户确认后 `git apply`，再补 `result.md`。
