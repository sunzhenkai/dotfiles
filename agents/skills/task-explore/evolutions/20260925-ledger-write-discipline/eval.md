# Eval — 20260925-ledger-write-discipline

对照生产稿 `agents/skills/task-explore/` 验证候选稿。目标 Skill 自带契约测试，跑测试 + 指令级对照。

评测方式：临时目录组装候选（生产 skill 副本 + 候选 SKILL.md + 候选 reference 入 references/ + 候选测试入 tests/），不触碰生产稿。

## 回归

- 契约测试 `tests/test_task_explore_contract.py`：原 39 条全过，新增 2 条亦过，**41 passed**。
- 既有成功路径未被新规则打断：archive/reopen 的批量改路径在纪律第 3 条显式开口（父路径前缀匹配 + 被改行数=子任务数），与 `phase-archive.md:29`、`phase-reopen.md:25` 既有细则一致，不冲突。
- SKILL.md 候选 vs 生产 diff 恰为 2 处（加载节加写时门禁、索引节加写入纪律指向），无顺手重构、无夹带编辑。
- 绑定门、父任务禁 handoff 门、确认门、archive/reopen 五条/四条门禁原样保留。

结论：pass

## 模式

原失败三类：误删他任务索引行、表格列数损坏、重复编号。按新指令重放：

- 误删：第 3 条禁「按内容过滤后批量删除」，删除只许精确整行等值 + 行数恰减 1 断言 → 当场拦下。
- 列数损坏：第 2 条整行替换 + 列数=表头断言（5 列）→ 落错列即触发改回。
- 重复编号：第 4 条追加前读最大编号 + 追加后查重，覆盖 decide 的 D-n 列表 → 拦下。
- 锚点不唯一（8 次并发告警根因）：第 1 条写前重读 + 锚点计数恰为 1 → 不凭记忆盲写。
- 静默覆盖：第 5 条只新增自己的块 + 显式「更正/冲突」条目 → 不抹他人内容。

结论：pass

## 契约

- 自带测试已跑：41 passed（含新增 `test_ledger_write_discipline_is_gated`、`test_ledger_discipline_carves_out_batch_path_update`）。
- 新 reference 已登记进 `test_reference_files_exist` 清单。
- 指令级核对：5 条均为可执行检查（grep/计数/断言/改回/停止），无「注意」「尽量」「回滚」类软措辞。

结论：pass

## 副作用

- 触发范围未扩大：门禁只在「写台账时」触发，不写台账的阶段（chat/resume/explore 纯问答）不读、不受影响。
- 权限与破坏性操作无变化；只收紧写入纪律，不变松任何约束。
- 批量更新口子限定父路径前缀 + 行数断言，未给「任意批量删除」开门。
- 第 5 条未引入 TASK.md 没有的署名格式，不改 task-template.md。

结论：pass

## 结论

pass。候选 diff 与 proposal.yaml 一致，无夹带编辑。生产稿未改动，promote 待用户确认。
