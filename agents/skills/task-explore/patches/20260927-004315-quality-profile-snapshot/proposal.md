# 复杂档质量画像与显式降级原文快照在探索生命周期内不丢失

- target: agents/skills/task-explore
- mode: update
- patch: 20260927-004315-quality-profile-snapshot
- risk: medium
- status: proposed

## Intent

上游 `task-wizard` 复杂档交给 task-explore 的方案正文里含「质量画像」与「显式降级」两段原文。task-explore 的台账只登记目标、完成判据、事实、假设、步骤、阻塞点、坑，画像与降级既没有落点，也不参与 `decide` / `handoff` 门禁，于是会在 explore → design → decide → handoff 的某一跳被压成一句摘要或一个路径指针，交付端只剩功能项、质量底线与降级授权丢失。

要改变的行为：

1. `new` / `save` 落台账时，「方案」小节逐字登记上游传入的质量画像与显式降级原文快照；输入里没有就不编造。
2. `decide` 把该快照当作成功标准输入；存在确认状态为 `pending` 的显式降级时不得冻结，阻塞原因写明「降级未确认」，只有用户确认后才可 `decide`。
3. `design` 必须把画像快照逐字带进设计稿并展开成可检查的 UI / 数据 / 验收细节，不得用路径或小节指针替代原文。
4. `handoff` 的交接段与 taskflow `--goal` 携带画像与降级原文快照；仍有 `pending` 时停在交接门禁，不创建 driver。

非目标：不改生命周期状态机与 `status` 取值（仍 `ongoing` / `handed-off` / `archived`），不新增阶段，不改 handoff 目录规则、driver 命名、批量交接与 `reopen` / `archive` 语义；不改 task-wizard 的质量画像契约本身；不引入自动质量评分器。

## Conflict check

- `SKILL.md`「new」第 3 步与「方案」小节登记清单不含画像：不构成冲突。`new` / `split` 写文件时本就要求读 `references/task-template.md`（见「加载」表），登记落点与逐字要求由模板给出，无需在 `SKILL.md` 重复一份清单，避免两处漂移。
- `phase-decide`「Goal 里」允许审阅收敛即视为逐条确认并立刻 `handoff`，与「pending 降级须用户确认」相对：按 task-wizard 退出点「降级未确认」的语义收敛——该项不进审阅可放行集合，仍停等用户。已在本阶段内写明例外，不改 `SKILL.md` 的「Goal 里的确认」正文。
- `phase-decide`「压缩路径」的「视为已确认全部推荐默认值」会把 pending 一并扫过：补一句排除，防止压缩路径绕过确认门。
- `phase-handoff`「处在 goal 里时，不询问是否交接」同样可能与新门禁相撞：补例外说明，门禁 4 要的是用户确认而非审阅收敛。
- 新增门禁 4 后，父任务批量交接时 pending 子任务会命中「任一失败即停」：这是既有批量语义的正常后果，不改批量规则本身。
- 与 `phase-design` 边界「不写实现代码、不创建 OpenSpec `tasks.md`」不冲突：展开停在页面 / 交互状态 / 数据假设 / 验证方式层面，架构、接口、schema、代码骨架仍在不审不写之列。
- 与 `task-template`「没有则删去本行，不要编造」的既有写法一致，新行沿用同一措辞，不引入「无」占位以外的新约定。none 其余。

## Rationale

画像与降级的价值在于它们是**可检查的原文约束**：一旦在中途被概括或换成指针，下游就退回到布尔功能项，正是 ADR `adr-quality-profile.md` 要防的失效模式。因此本轮只做两件事——**逐字保留**（登记、设计、交接三处都要求原文快照，指针不算）与**授权不丢失**（`pending` 沿台账传递到 `decide` 与 `handoff` 两道门禁，确认权只属于用户）。改动全部落在既有 reference 的门禁与步骤文本上，措辞通用、无项目专有内容，可随 skill 分发；每条都可机械核对：台账有无快照原文、决策是否含 pending、设计稿是否逐字、`--goal` 是否带原文。不触碰状态集合、目录规则与 driver 命名，风险集中在工作流与输出契约，判 medium。

## Files

- `agents/skills/task-explore/references/task-template.md` — 「方案」小节说明补逐字登记质量画像 / 显式降级原文快照；模板新增两条快照行；交接段新增快照行（供 handoff 落点）
- `agents/skills/task-explore/references/phase-decide.md` — 门禁补两条：快照属成功标准输入、pending 降级不得冻结（阻塞原因「降级未确认」，仅用户确认）；「Goal 里」与「压缩路径」各补一句排除
- `agents/skills/task-explore/references/phase-design.md` — 门禁补一条并新增「画像展开」小节：逐字复制快照后展开为可检查 UI / 数据 / 验收细节，路径指针不能替代原文
- `agents/skills/task-explore/references/phase-handoff.md` — 单任务交接门禁新增第 4 条（pending 即停、不建 driver）；步骤 2 交接段与步骤 3 `--goal` 携带原文快照；「处在 goal 里」补例外

## Validation

- 应用前（仓库根）：`git apply --check --recount agents/skills/task-explore/patches/20260927-004315-quality-profile-snapshot/change.patch`；确认 patch 只触及 `agents/skills/task-explore/references/` 下这 4 个文件，不含 `patches/` 历史、镜像目录、绝对路径。
- 应用后：`git diff --check -- agents/skills/task-explore`；核对实际 diff 与本 proposal 一致；`SKILL.md` frontmatter 合法且 `name` 与目录名一致（本轮不改 `SKILL.md`）；`references/` 内链接与新增小节标题可达；无隐私与项目专有内容。
- 行为核对（人工读语义）：`status` 取值仍为 `ongoing` / `handed-off` / `archived`；阶段表与加载表无改动、未新增阶段；handoff 目录与 driver 命名规则不变；输入不含画像时四处新规则均落到「不编造 / 视为不适用」分支，简单与中等档行为不变。
- 本 patch 不自动应用、不 sync、不 commit；应用需按 medium 门禁取得用户确认后 `git apply`，再补 `result.md`。
