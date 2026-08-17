# Apply 阶段

执行前读根 `SKILL.md`，并遵守 `safety.md` 的 RES-1/3、CHECKOUT-1/2/3/4、APPLY-1/2/3/4/5/6/7、DELEG-1、MUT-1；规则正文只在 `safety.md`，本文件不复述。本文件是 apply outcome 契约与汇报模板的唯一来源。

## CLI 驱动

调度靠 CLI 返回值，不靠记忆：`execution-context` 与 `advance` 都返回 `next_action{summary, command, forbidden}`。

- `command` 非 null 即下一条要跑的 taskctl 命令；先做完 `summary` 指的实施动作，再原样执行（checkbox 原文已转义内联，不要改写）。
- `forbidden` 是本轮禁止动作：`testing`/`done` 指阶段转换，`claim_complete` 指对外宣称完成，`schedule_candidate` 指继续调度候选项，`assume_not_started` 指把状态未知的上次处理项当作未开始。
- `next_action` 是派生视图，与顶层 `result` 冲突时以 `result` 为准（APPLY-1）。
- `advance --phase implementing` 另返回 `budget{items_since_report, should_report}`；`should_report=true` 是汇报点，套暂停模板汇报后继续，`result` 不变。

## 入口：首次实现与续作

两条入口都先 `resolve <id> --command task-apply`；命中 archived task 时报告后 `restore <id> --status in_progress` 再 resolve。

- **首次实现**：先 `prepare-branches --slug <slug> --from-task <id>`，再 `execution-context <id>`。
- **续作**：直接 `execution-context <id>`，只在 `resume.prepare_required=true` 时补跑 `prepare-branches`（APPLY-6）。
- 只查进度不实施：`status <id>`，不调 git、不过 checkout gate，binding 未就绪也可用。

`prepare-branches` 只处理必须仓（CHECKOUT-1/3）：任一仓 blocked 即整次准备不算成功，已成功仓的 binding 保留以便重试；`dirty_role=planning` 附 `planning_action`，准备照常继续。

## execution-context 事实

只以 JSON 为准，不从叙述文本反推：

| 字段 | 用途 |
|------|------|
| `checkout_gate` | delivery binding 校验结果（CHECKOUT-4）；失败时按 `next_action` 决定补跑准备还是等用户处理 |
| `openspec_locations` | change 只在 canonical planning root 读写，不随交付分支移动；`readable=false` 时按 `action` 处理，不得改用 delivery 路径 |
| `apply_schedule.groups` | 按 change 分组的进度、候选与暂缓；`candidates` 已排好序，直接顺序取用 |
| `resume` | 上次阶段、上次处理项及其状态、是否需补跑准备、delivery 未提交改动、验证新鲜度 |

`resume.last_item_state` 决定续作起点：`completed` 取下一个候选；`in_flight` 表示改了一半，先读 `resume.uncommitted` 判断归属再接着做；`not_started` 正常开始；`unknown` 时 `forbidden` 会含 `assume_not_started`。

无 OpenSpec target 时停止并建议 propose。

## 实施与 candidate 依赖检查

`candidates` 只表示“未显式 defer 且 artifact 可读取”，**不表示依赖已满足**：每个 candidate 执行前读 task/design 上下文，按 APPLY-2/7 判断依赖并处理。

- 独立 candidate：实施；完成后先勾选 canonical planning root 下对应 `tasks.md`，再 `advance <id> --phase implementing --change <change> --completed "<checkbox 原文>"`。仓级测试只写入 `--completed` / `--verification` 文本。
- 依赖 deferred 项，或因环境/凭据/人工验证局部不可执行：保持 checkbox 未勾选，用 exact `--change` + `--current-task` 调 `--defer-current "<原因含 blocker identity>"`；阻塞解除后同 change/task 用 `--resume-current` 恢复。
- 只有全局故障或需用户决策时才用 `--phase blocked --blocker ...`。

## Outcome 控制

只依据顶层 `result`；候选事实不能覆盖 phase outcome。「停」只结束本轮 candidate 调度，不是 task 完成，也不是任何宿主完成信号（APPLY-5）：

| result | 写入 status | 触发条件与本轮行为 |
|--------|-------------|----------|
| `blocked` | `blocked` | 全局故障或待用户决策；停本轮调度，candidates 非空也不得继续 |
| `next` | `in_progress` | 有独立候选；同轮继续处理 `next`，已 defer 项并行挂起 |
| `deferred_only` | `in_progress` | 无独立候选；汇总 deferred 与阻塞身份后停本轮调度 |
| `validation_required` | `in_progress` | checkbox 耗尽但无 fresh verification，或证据仅 provisional；停本轮调度 |
| `validation_recorded` | `in_progress` | clean delivery 的最终验证已记录；只进入 done transition |
| `done` | `in_progress` | checkbox 与 fresh verification 均满足；桥接 archive |

## 汇报模板

对外汇报套模板，不自由发挥。只有 `done` 才允许套完成模板，其余 outcome 与汇报点一律用暂停模板。

### 暂停

```text
本轮以 `<result>` 结束（未完成）。
- 已完成：<本轮记账的 checkbox 原文，逐条>
- 剩余：<openspec_remaining.remaining> 项，其中暂缓 <deferred 数>
- 暂缓/阻塞：<change: checkbox 原文 — 原因或 blocker identity>
- 下一步：<next_action.summary>
```

### 完成

```text
`advance --phase done` 返回 `done`，task 交付完成。
- 完成范围：<每个 change 的 complete/total>
- 验证证据：<progress.md 最终验证快照>
- 下一步：{{slash:task-archive}} <id>
```

## 节奏（建议，非硬门禁）

- **单轮预算**：`budget.should_report=true`（默认每 5 个 candidate）或累计 60 分钟先汇报并等确认；墙钟无状态 CLI 计量不了，靠本条自律。
- **委托上限**：子 agent／并发评审设墙钟上限（默认 15 分钟）与连续失败上限（2 次），超时或超次降级为主会话自审，把结论写进 `--verification` 后继续调度；硬约束（不得判 blocked、不得成为 candidate 必经路径）见 DELEG-1。
- **验证分层**：implementing 只跑受影响范围的 targeted 验证，全仓回归、race 与静态检查留到 testing 一次性执行。
- **不另起炉灶**：续作只从 `resume` 取事实，不得改用第二套 apply 流程（如直接走 `openspec-apply-change`）。

## 验证与完成

证据强度规则见 APPLY-4（仓级测试不是 final verification，dirty 证据仅 provisional，实现恢复或 branch/HEAD 变化使 snapshot stale）；本阶段的动作顺序是：

1. 提交或清理全部 delivery checkout：**delivery 提交归本阶段负责**，可委托 skill `commit-push`；planning 产物留在 canonical planning root，不必为过本门而提交。随后 `advance <id> --phase testing --verification "<命令与结果>"`。
2. 用同一份证据回填 README 验收标准：逐条勾选，未达成项保持未勾并写明原因，使 archive 的未勾选确认只剩真正未达成项。
3. 再跑 `advance <id> --phase done`；返回 `stale_verification` 就按上条规则重测。
4. `done` 后桥接 `task-archive`，archive 会再次执行相同 checkout 与 final snapshot 校验。

## 回路与例外

- 实现中发现 **change 本身有误**（契约写错、拆分不对、缺 spec）：停止该项，`advance --phase blocked --blocker "<change>: <问题>"` 记录，桥接 `{{slash:task-propose}} <id>` 修正后再回 apply；不在 apply 里改写 change 语义。
- 跨 task 定位用 `list`（`--archived` 看归档）。apply 期间 status 由 `advance` 写入，只有 apply 之外的人工改状态才用 `set-status`。
