# Driver proposal 与验收标准承接上游质量画像和显式降级

- target: agents/skills/taskflow
- mode: update
- patch: 20260927-004315-quality-profile-acceptance
- risk: medium
- status: proposed

## Intent

复杂产品交付的画像与降级表在交给 taskflow 时被摘要掉，driver proposal 只剩功能动词，验收标准里没有任何质量底线与降级确认，交付结果退化成 demo。ADR（`tasks/ongoing/agent-delivery-quality/design/adr-quality-profile.md`）已决定「画像原文进入 taskflow proposal 和验收标准」；task-wizard 侧 patch `20260927-003054-quality-profile-gate` 把「画像快照的下游登记」显式留作后续 patch，本轮即该下游登记。

要改变的行为（全部在 `agents/skills/taskflow/SKILL.md`）：

1. `### driver `proposal.md` 模板` 的说明段补充：任务描述含质量画像原文或显式降级表时，`Why` 逐字保留该快照，不摘要、不改写、不用小节指针或路径替代；任务描述没有这些内容时不编造画像与降级条目。
2. 同处的验收标准填写规则补充：有画像时，除完成判据原文外至少再写三条——画像原文快照已逐字进入 proposal、每条角色底线写明验证方式（运行时行为 / 截图 / 测试证据）、`pending` 降级数为 0；`confirmed` 降级在验证记录里逐项写明维度、实际选择与用户确认来源以保持可追踪。
3. `### 脚手架输出` 补充：仍需用户确认的空缺必须逐条列出每个 `pending` 降级（维度 / 默认期望 / 实际选择 / 原因），不合并成汇总条目，不由 agent 代用户确认。
4. `## 纪律` 新增 `### 质量画像与降级确认` 小节：子 change 实施中发现新的生产性降级（比默认期望少交付都算，改名成「技术选型」「本期简化」也一样）时标 `pending`、写入 driver `proposal.md` 的验证记录，并作为需要用户决策的项停下等用户；用户点名确认后才允许勾相关验收标准 checkbox，并在验证记录记为 `confirmed`。
5. 非目标：不改 Driver 协议固定文本（逐字拷贝源保持原样）；不改编排协议、子 change 命名 `{task}-<slice>`、kebab-case 归纳、`skip_specs: true`、tasks.md 留给 propose 的时机、委托契约、并行执行与 Self-evolution 注入块；不复制 quality-profile 的字段清单进 taskflow；不在本 patch 给 `evals/cases.yaml` 加新 case；不同步 `openspec/` 下任何 spec。

## Conflict check

- `evals/cases.yaml` 的 `driver-protocol-verbatim`（must_not 改写、精简或挪走 Driver 协议）与 `scaffold-three-steps`（must_not 改写 Driver 协议固定文本）：本 patch 的三处改动全在模板 fenced 块与纪律的模板指针句之外，Driver 协议正文一行不动。
- `scaffold-three-steps` 的 must「报告 change name、proposal 路径与待确认空缺」仍成立，`pending` 降级是空缺清单里新增的一类条目，不是新的报告步骤；must_not「脚手架阶段写 tasks.md」未受影响。
- `checkbox-ssot` 的 must_not「持久化第二份完成度、暂缓或分支状态记录」：新规则把 `pending` / `confirmed` 写进 driver `proposal.md` 已有的验证记录小节，与「暂缓原因写进验证记录」同一处，taskflow 仍不建第二份账本、不补脚本。
- `round-end-three-only`：新纪律显式挂靠三条件里的「需要用户决策」，并声明不依赖该决策的其余条目仍按「一轮结束」继续处理，不与「不因一项卡住就整轮停下」冲突；「用户确认前不勾相关验收」与该 case 的 must_not「把未完成项勾成完成」同向。
- `fail-closed-must-repos` / `并行执行` 的子代理约束（不勾 driver 编排项）：新规则只增加「确认前不勾相关验收标准」，与既有纪律同向，不改变派发与汇总职责。
- 与 task-wizard `references/quality-profile.md` 的降级语义一致（`pending` 只能由用户改 `confirmed`，执行者 / 审阅者 / 评审收敛都不算确认），但**不**跨 skill 引用该文件路径——taskflow 需可独立分发，字段清单由上游任务描述带入，本 skill 只写门禁动作，避免双处维护字段定义。
- 与 task-wizard 侧 proposed patch `20260927-003054-quality-profile-gate` 不互相改写：那轮管复杂档 Goal 的画像门与派审，本轮管 driver 的登记与验收；两份 patch 各自 `status: proposed`，可独立应用。
- 其余：无冲突。

## Rationale

「功能存在」不等于可交付，画像里的隐含要求一旦被摘要就不可检查。保留逐字原文快照是最小的防丢手段；把验收写成三句可机械核对的话（快照是否进入 proposal、每条角色底线是否带验证方式、`pending` 计数是否为 0），使 driver 的 checkbox 能承载质量门而不需要评分器或新状态。降级确认独立于执行者与审阅者授权，只有用户能放行，避免 agent 单方面放弃约束后仍把验收勾成完成；规则命中既有的「需要用户决策」结束条件，因此不改状态机与一轮结束语义。改动全程用通用措辞与既有术语，不含项目专有页面名、主机路径或内部 URL，可随 skill 分发。

## Files

- `agents/skills/taskflow/SKILL.md` — `### driver `proposal.md` 模板` 说明段新增 `Why` 快照一句与画像验收段；`### 脚手架输出` 新增 `pending` 降级列入待确认空缺的一句；`## 纪律` 在 `### 涉及面与交付分支` 与 `### 一轮结束` 之间新增 `### 质量画像与降级确认` 小节。

## Validation

- 应用前（仓库根执行）：`git apply --check --recount agents/skills/taskflow/patches/20260927-004315-quality-profile-acceptance/change.patch`。
- 应用后：`git diff --check -- agents/skills/taskflow`；核对实际 diff 与本 proposal 一致且不含 Driver 协议 fenced 模板块、`skip_specs` 说明段、**不要写 `tasks.md`** 段、子 change 命名与委托契约的行；`SKILL.md` frontmatter 合法且 `name` 与目录名一致；grep 确认 `evals/cases.yaml`、`examples/`、`experience/` 与历史 `patches/` 未被触及；无隐私与机器路径。
- 行为核对（人工读方案）：任务描述不含画像时不新增画像类验收条目；`pending` 降级数大于 0 时相关验收不允许全勾；`confirmed` 降级在验证记录可追踪；脚手架输出仍提示 propose 应选「继续已有 change」。
- 本 patch 不自动应用、不 sync、不 commit；medium 风险需按 skill-upgrader 门禁取得用户对 diff 的明确确认后再 `git apply`，并补 `result.md`。
