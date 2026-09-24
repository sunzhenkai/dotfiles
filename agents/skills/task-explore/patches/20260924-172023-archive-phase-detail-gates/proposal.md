# task-explore：补齐 archive 阶段细则并同步契约测试

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-172023-archive-phase-detail-gates
- risk: medium
- status: proposed

## Intent

`archive` 是探索任务的生命周期终点，却是全 skill 检查最单薄的阶段：只有 SKILL.md 里 8 条步骤，且 `references/` 下没有细则文件（加载表把 archive 归进「本文件已够」，而 explore/design/plan-review/decide/handoff 各有独立 reference）。本轮补齐 archive 的收口检查，并把细则移到 reference、SKILL.md 只留不可跳过的硬门禁（与 handoff 同构）。

新增的清点项：

- **关闭原因留痕**：归档必须写 `已交付 / 放弃 / 被 {task} 取代 / 其它` + 一句话，取自用户回答。
- **未决清点**：报告未勾项条数与首条，问「随任务关闭」还是「先补结论」；明确**不要求清零**（带着未决关闭是合法结局，静默关闭才是问题）。
- **交付侧核对**：曾 `handed-off` 的任务归档前读 driver 的 openspec 进度并报告「已完成 X/Y」，读不到报「进度未知」不当作已完成；只报告不回写，保持 handoff 单向桥不变。
- **入链检查**：搜索 `tasks/` 内指向旧路径的父↔子、`design/` 互链，问是否改指新路径，拒绝则记「保留断链」。
- **INDEX 文案规则**：handed-off 行保留 `→ {task-name}-driver` 尾注；父任务聚合描述改成闭合态，不留「设计中」这类进行时。
- **搬完自证**：旧路径已空、新 `TASK.md` 可读、INDEX 每条归档路径实际存在；不一致报漂移并按索引规则重建。
- **日期一致**：`archived` 日期在元信息、目录名、INDEX 三处同一个 `{yyyy-mm-dd}`。
- **可用性护栏**：多条门禁同时命中时合并成一次确认，不逐条往返；并显式保留「只给任务名不算确认，未拿到「确认关闭」答复不搬」，避免细则迁入 reference 时弱化这条最高门禁。

非目标：不改 frontmatter description 与触发条件；不做 driver → 探索任务的状态回写；不加批量归档语义；不动 `reopen` 流程；不迁移存量 archived 任务。

同一轮附带把契约测试同步到已应用的 handoff/archive 解耦语义（见 Rationale），并为本轮新增门禁补断言。

## Conflict check

- 与 SKILL.md 现有 archive 段是**收紧替换**：步骤整体迁入 `references/phase-archive.md`，硬门禁（目标冲突零副作用、子任务结清）逐字保留。
- 与 `references/task-template.md` 的归档尾注耦合：该处只补一句指向新「归档」小节，不新增骨架小节（避免每个新 TASK.md 带空归档节）。
- 与 openspec `task-explore-lifecycle` spec 无冲突：spec 只规定目标路径冲突、handed-off 归档警告与父任务门禁（spec.md:32-42、109-118），本轮全部保留并只做加法。若要把新门禁提升为 spec 要求，需另走 openspec change，不在本 patch 内。
- 与 `phase-handoff.md` 职责边界：交付进度仍只认 taskflow checkbox，archive 只读不写，桥仍单向。
- 测试文件当前 6 条失败断言的是解耦前的旧措辞（`无决策则先 decide`、`必须等于探索任务 slug`、`仅当 driver 已存在`、`禁止 handoff`、`原地归档`、`移动目录到 ongoing/`），属历史 patch 未同步，与本轮方向一致，无对冲。

## Rationale

archive 后仅剩 `status: archived` + 日期，三种结局（做完 / 放弃 / 被取代）在台账里长得一模一样；`decide` 要求未决逐条确认，生命周期终点却没有对应收口；父归档整树搬家后跨文件引用静默失效。这些都会让 `reopen` 和后来者无法判断该不该复活任务。改动全部是可执行、可验证的文本门禁，且以 `pytest tests/test_task_explore_contract.py` 为确定性验证（scratch 预跑 29 passed）。

## Files

- `agents/skills/task-explore/SKILL.md` — archive 段改为「硬门禁 + 指向 reference」；加载表新增 archive 行，末行收回到 `chat / resume / reopen`
- `agents/skills/task-explore/references/phase-archive.md` — 新建：5 条门禁 + 7 步流程 + 归档记录四要素
- `agents/skills/task-explore/references/task-template.md` — 归档尾注补「归档」小节与三处日期一致
- `agents/skills/task-explore/tests/test_task_explore_contract.py` — 6 条失效断言同步到解耦后语义；archive 顺序测试改读 reference；新增 10 个测试（9 个 archive 门禁 + 1 个 handoff 不归档），用例数 19 → 29

## Validation

- 应用前：`git apply --check --recount agents/skills/task-explore/patches/20260924-172023-archive-phase-detail-gates/change.patch`（已通过）
- 应用后：`git diff --check`；`python3 -m pytest agents/skills/task-explore/tests -q` 全绿；frontmatter `name` 与目录一致；`references/phase-archive.md` 链接存在；无隐私内容
