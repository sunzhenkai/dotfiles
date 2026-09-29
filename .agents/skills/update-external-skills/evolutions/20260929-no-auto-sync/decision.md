# decision — 20260929-no-auto-sync

**promote**（2026-09-29）

晋升前核对：

- 用户本轮主动提出「不应执行 `dotf agents -c` 同步与 commit/push，应作为下一步提示」，并对本 Proposal 与候选 diff 明确确认晋升。
- eval 结论 pass；唯一代价（上游哈希独立复验移出必经路径）已写入正文第 2 步并给出补救条件，未隐藏。
- 改动与本 Proposal 的 proposed_change 逐条对应；坑 1–3、5–6、8、10–14 与底稿逐行一致，无夹带无关编辑；未触碰 `src/` 任何行为。
- 底稿 `20260929-scripted-verify`（未晋升）的脚本化改动随本次合并候选一并落地，该目录已标记 superseded。

晋升后动作：项目级 skill 由仓库直接加载，无需安装通道同步；`~/.agents` / `~/.claude` / `~/.kiro` 均无本 skill 副本（已核对）。**未代为 commit / push**——按本稿新规则，提交交回用户。
