# Apply 阶段

执行前读根 `SKILL.md` 与 `safety.md`。本阶段把 OpenSpec change 的 checkbox 逐项实现掉；**checkbox 是唯一进度真相**，不维护第二份进度文件。

## 入口

1. `resolve <id> --command task-apply`。命中已归档 task 时按提示确认后 `restore <id>` 再 resolve。
2. `status <id>` 读事实：涉及面、工作上下文、每个 change 的 `complete/total` 与 `remaining`。
3. 工作上下文为空（或 `status` 显示仓库尚未准备）时跑 `prepare-branches <id>`，否则直接续作。
   - `prepare-branches` 只切涉及面里的 `必须` 仓（CHECKOUT-1）。
   - 退出码 2 时原样报告 `blocked` 并等用户处理；已 ready 的仓会保留，处理完直接重试同一条命令（CHECKOUT-2）。
4. 无 OpenSpec target 时停止并建议 `{{slash:task-propose}}`。

续作不需要特殊命令：`status` 里已勾选的就是做完的，未勾选的就是待做的。不要另起一套 apply 流程（例如直接走 `openspec-apply-change`）。

## 实施循环
对所有 change 的 `remaining` 逐项处理。README「关联 OpenSpec」表的行序只是**优先顺序，不是串行门**：前一个 change 未完，不阻止后面 change 中不依赖它的项（APPLY-2）。
每项：
1. 读 task README、`design/`（若有）与 change artifacts，判断这一项的前置依赖是否已满足。`remaining` 只说明「没勾」，**不说明依赖已就绪**。
2. 依赖未满足、或因环境/凭据/人工验证局部不可执行：**保持 checkbox 未勾**，在 README 验证记录小节记一行「暂缓：`<change>` / `<checkbox 原文>` — `<原因含阻塞身份>`」，然后**继续下一项**。暂缓只作用于该 checkbox 本身（APPLY-2）。
3. 可执行：实现，跑受影响范围的 targeted 验证，然后在该 change 的 `planning_root` 下勾选 `tasks.md` 对应 checkbox。全仓回归留到收尾一次性跑。
4. 已勾选的项不重复审阅。
暂缓记录只允许 `- 暂缓：<change> / <checkbox 原文> — blocked-by <change>:<checkbox 编号>；<原因>` 或把 `blocked-by ...` 换成 `external <任务范围外的明确身份>`；前三个身份按 Markdown 反引号包裹，checkbox 内部反引号写成 `\``。
`blocked-by` 只引用同一 task 内真实存在且未勾选的精确 checkbox；依赖完成后该记录立即失效并必须重判。不得把本 checkbox 负责实现的契约、同一交付范围内的笼统 “owner” 写成 external，否则是自循环阻塞，不是暂缓理由。依赖还必须**直接**：`blocked-by` 指向的项自己也被暂缓时判 `transitive_deferral` 作废——顺着链条挂下去，一个根阻塞就能合法吞掉整个 task，链上的项要么直接对根阻塞重判，要么本来就该继续做；单个 blocker（`blocked-by` 目标或 `external` 身份）覆盖超过 20 项或 remaining 的 25%（不足 4 项不算）判 `cascade_suspected`，一条记录再规范，几百条挂在同一个阻塞上也说明这些项根本没被逐项判过。
## 本轮结束条件

只有下面五种情况允许结束本轮（APPLY-1）。「余下每一项都已逐项暂缓」**不再是**独立的结束理由——它等价于这个 task 一项都动不了，走全局阻塞那行：

| 情况 | 处理 |
|------|------|
| `remaining` 已全部勾选 | 走收尾 |
| 本轮预算耗尽：上下文、时间或轮次上限到了，还有项没来得及逐项判定 | 套「本轮结束」模板，如实分开「暂缓」与「未判定剩余」，给出续跑锚点 |
| 需要用户决策：方案分歧、缺授权、change 本身有误 | 提问并等待 |
| **全局阻塞**：每一项 remaining 都动不了 | `set-status <id> blocked`，把每个根阻塞的解除条件（找谁、要什么）摆给用户等处理。**不套「本轮结束」模板**——那读起来像正常暂停，实际是要人来解 |
| 全局故障：交付仓不可用、工具链坏、`prepare-branches` 退出码 2 | 原样报告并等用户处理 |

其余情况一律继续下一项——**刚做完一项、刚到汇报点、刚记下一条暂缓、子 agent 委托失败，都不是结束理由**。

预算耗尽是诚实出口，不是省事出口：**不得把没判定过的项说成暂缓**（APPLY-3）。**暂缓**是已读过该项、判过依赖、README 里有对应那一行的项，报告须逐条给出 `<change>` + checkbox 原文 + 原因，行数必须等于声称的暂缓数；**未判定剩余**是还没轮到的项，按 change 给出数量与首个 remaining 原文即可，不要编原因。剩余只按 change 报成几个总数是未判定项冒充暂缓的典型形态。结束前必须运行 `validate-round-end <id> --reason all-deferred|budget-exhausted`（APPLY-4），命令失败不得结束。`all-deferred` 是对账入口不是通行证：级联、无效、陈旧或 uncovered 都具名失败，而**全部合格恰恰说明这个 task 一项都动不了**，CLI 判 `task_fully_blocked` 要求改走 `set-status blocked`——它永远不会放你套「本轮结束」模板。`budget-exhausted` 把 uncovered 归为 `unjudged`，并把级联暂缓一并降级为未判定，假暂缓换不来任何进度声明；报告按 CLI 返回的 `deferred_count` 与 `unjudged_count` 写，别用自己记的数。每完成一个 checkbox 都重新 `status`；依赖已勾选必须回头重判，禁止沿用陈旧依赖闭包。

## 汇报节奏

每约 5 项或累计约 60 分钟，用「进行中」模板汇报一次并**立即继续**，不等用户回复。预算真的见底时走「本轮结束」模板的预算耗尽分支收尾，把已判定与未判定分清楚——汇报点本身仍然不是结束理由。委托子 agent 或并发评审时自设墙钟上限（约 15 分钟）与连续失败上限（2 次），超时就降级为主会话自审后继续——委托失败不等于任务 blocked，也不能成为某一项的必经路径。同步宿主 Task/Todo 工具时必须原样回传其 ID，不自行添加 `#` 等展示符号。

## 收尾

全部 checkbox 勾完后：

1. 提交或清理所有交付仓的改动。**交付提交归本阶段负责**，可委托 skill `commit-push`；planning 产物留在 canonical planning root。
2. 跑全仓回归与静态检查，把命令与结果写入 README「验证记录」小节。
3. 用同一份证据回填 README 验收标准：逐条勾选，未达成项保持未勾并写明原因，好让归档时的确认只剩真正未达成的。
4. 桥接 `{{slash:task-archive}} <id>`。

## 汇报模板

### 进行中（汇报点，输出后立即继续）

```text
进度汇报（继续中）。
- 本轮已勾选：<checkbox 原文，逐条>
- 剩余：<status 的 remaining 合计> 项，其中暂缓 <数量>
- 继续处理：<下一项的 change / checkbox 原文>
```

### 本轮结束（未做完）

```text
本轮结束（未完成）。
- 结束原因：<上表四种之一>
- 已完成：<本轮勾选的 checkbox 原文，逐条>
- 剩余：<status 的 remaining 合计> 项 = 暂缓 <n> 项 + 未判定 <m> 项
- 暂缓：<change: checkbox 原文 — 原因>（逐条，行数必须等于 n）
- 未判定剩余：<按 change 给出数量与首个 remaining 原文>
- 续跑锚点：<下一轮从哪个 change 的哪一项开始>
- 下一步：<具体动作>
```

### 完成

```text
全部 checkbox 已勾选、验证已记录，交付完成。
- 完成范围：<每个 change 的 complete/total>
- 验证证据：<README 验证记录摘要>
- 下一步：{{slash:task-archive}} <id>
```

只有 checkbox 全勾且验证已写入才允许套完成模板。结束本轮不等于 task 完成，task 保持 `in_progress`。

## 回路与例外

实现中发现 **change 本身有误**（契约写错、拆分不对、缺 spec）：停止该项，`set-status <id> blocked`，桥接 `{{slash:task-propose}} <id>` 修正后再回 apply。不在 apply 里改写 change 语义。
