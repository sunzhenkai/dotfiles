# eval — 20260929-no-auto-sync

对照现有行为验证，非文案完整度。底稿 = `evolutions/20260929-scripted-verify/SKILL.md`（未晋升）。

## 回归（成功路径是否被新规则打断）

| 原路径 | 候选稿结果 | 判定 |
|---|---|---|
| 重锁并拿到 `sources=N blocked=0` | 第 1 步原文保留，只加一条「唯一必经网络成本」提示 | 未打断 |
| 判定内容是否真变（含 added/removed 改名信号） | 改由 `lock_verify.py changed` 单独承担，计数语义不变；坑 12 的 added+removed 判读保留 | 未打断 |
| 下发分段解读表 | 整段搬入「下一步」，逐字保留 | 未打断 |
| sync 失败定性（stale owned / without ownership） | 保留在「下一步」段，坑 13 未动 | 未打断 |
| 上游哈希 + 三 layout 核对 | 随 `verify` 整体移到下发之后；脚本无哈希/落地分离入口 | **有代价，见下** |

**已认下的回归**：`tree_hash == content_hash` 的独立复验不再是必经步骤。lock 的 content_hash 由 `lock_update.py` 在自己的 checkout 上算出（写入方自报），原第 4 步是唯一独立复验点。候选稿已在第 2 步写明该代价与补救条件（采信非自审 revision 前必须先完成下发与核对），不做隐藏。

顺序约束经代码确认为真，不是推测：`lock_verify._check_layout` 用 `source_root=staging`（新取的上游字节）编译计划再比对磁盘目标，故未下发就跑 layout 核对必然对变化条目报错——把哈希复验留在流程内只会产生假失败。

## 模式（原失败/重试能否避免）

- 下发不再必经 → 那一步的实测成本与跨三 layout 的全量重写不再每轮发生。
- 收尾三项（sync / commit / push）硬禁止 → 未授权的本机覆写与 git 历史改动失去发生条件；本轮那类「提交范围出错再 reset 返工」不再可能。
- 「verify 同一轮只跑一次，看明细就在同一次带 VERBOSE」→ 按条目取回的上游次数不再翻倍。

## 契约（目标 Skill 自带测试？跑既有测试，不编造分数）

- 目标 Skill 无自带测试，做指令级 + 工具级对照：
- `python3 src/agents/lock_verify.py changed` 实测 **exit 0 / 0.11s**，输出 `changed_content=0 changed_revision_only=0 added=0 removed=0`，证实第 2 步声明的「纯本地、不打网络」成立（锁已提交后工作区与 HEAD 一致，故计数归零，同时反证其比对对象是 HEAD vs 工作区）。
- `make registry validate` 本轮已过（第 3 步保持可用）。
- `tests/test_agents_lock_verify.py`：9 passed。
- skills-store 审计脚本对候选目录与底稿目录双双「通过（未发现风险模式）」。
- frontmatter YAML 可解析，键为 `name` / `description`。

## 副作用（触发范围 / 权限 / 破坏性动作）

- 触发面：description 去掉「并下发本机」，保留「同步 skill 上游」等原触发词——触发条件未收窄到漏召，改变的是流程内的动作授权。
- 权限方向为**收紧**：收回 sync、commit、push 三项，未放宽任何破坏性操作；坑 10「别顺手覆盖陈旧副本」原样保留。
- 成本：必经路径少一次 390s 级动作与一轮网络取回；未新增脚本或 target。
- 与底稿的重叠：diff 74 行，改动集中在 frontmatter、第 2/3 步、「收尾」与「下一步」两段、坑 4/7/9、边界；坑 1–3、5–6、8、10–14 与底稿逐字一致（已逐行 diff 核对）。
- 未夹带工具改动：`acquire_all` 按 source 去重、CLI 子集入口两项写入「边界」作为仓库侧后续，本 patch 不碰任何 `src/` 行为。

## 结论

**pass**（附一项已声明代价：上游哈希独立复验移出必经路径，补救条件写进正文）。

晋升需用户同时确认本 eval 与候选 diff；晋升后提醒经安装通道同步，不代为 sync 或提交。
