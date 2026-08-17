# task-workflow 安全契约

只保留会造成错误写入、进度丢失或错误结案的硬规则。测试是 case 细节的 SSOT，末列只给代表用例；改规则必须同步改测试。

| ID | 触发条件 | 必须行为 | 回归测试 |
|----|----------|----------|----------|
| RES-1 | 本条或本会话已有唯一 `TNNNN` / task 路径 | 显式传给 `resolve`，不得丢掉焦点改走启发式 | `test_resolve_by_id` |
| RES-2 | 只有 status / 关键词等启发式候选，或候选不唯一 | CLI 返回退出码 2；确认前不写 task | `test_resolve_ambiguous_needs_confirm` |
| PLAN-1 | new / explore / design / propose | 不为 task 分支运行 fetch/checkout；工作上下文保持「尚未准备」 | `test_status_works_before_branches_are_prepared` |
| CHECKOUT-1 | apply 准备仓库 | 只处理涉及面角色=`必须`；不把 cwd、建议仓或排除仓自动加入 | `test_prepare_branches_touches_only_must_repos` |
| CHECKOUT-2 | 非目标分支存在 dirty，或 origin fetch 失败 | fail closed 并等用户处理；禁止自动 stash、reset、force checkout。已准备成功的仓保留以便重试 | `test_prepare_branches_blocks_dirty_and_keeps_worktree_intact` |
| APPLY-1 | apply 每处理完一项后判断是否继续 | 只有「remaining 全部已勾或已逐项暂缓」「需用户决策」「全局故障」三者之一才结束本轮；汇报点、单项暂缓、委托失败都必须继续下一项 | `test_apply_round_end_conditions_are_pinned` |
| APPLY-2 | 某项因依赖或环境不可执行 | 暂缓只作用于该 checkbox：不得按 change 粒度整体推断，不得停掉同 change 其余项或后续 change 中不依赖它的项 | `test_deferral_does_not_cascade_across_changes` |
| PROG-1 | 判断实现进度或完成度 | 只认 OpenSpec `tasks.md` 的 checkbox（`status` 返回统计）。不得新增第二份进度、deferred 或 checkout 真相源 | `test_no_parallel_progress_state_files` |
| PROXY-1 | 委托任何 `openspec-*` skill | 必须在该 target 的 `planning_root` 下执行且显式传 change name，二者缺一不得委托；propose 收尾与 archive 外部动作前先跑 `openspec validate --strict --change <name>` | `test_openspec_delegation_contract_is_pinned` |
| ARCH-1 | 归档 | 先 `archive --dry-run`；checkbox 未完、验收未勾、交付仓 dirty 一律退出码 2，只传用户确认的 `exact_action`。change 未归档前不得 finalize | `test_archive_refuses_finalize_while_change_active` |
| DATA-1 | 涉及面 / OpenSpec / 工作上下文表格 malformed 或角色未知 | 具名失败，不猜默认值 | `test_unknown_scope_role_fails_closed` |

## 仓库角色

| role | 来源 | 约束 |
|------|------|------|
| delivery | 涉及面里的 `必须` 仓 | `prepare-branches` 切分支；archive 要求 clean |
| planning | change 所在仓的 `openspec/` | 读写 change artifacts；不切分支 |
| reference | `建议` / `排除` 仓 | 只读，不切分支、不查状态 |

同仓多角色时 delivery 优先。工作区根 `.` 仅在它自身确为必须修改仓时才是 delivery。

## 状态所有权

| 事实 | 唯一来源 |
|------|----------|
| task 身份、status、涉及面、验收、验证记录 | task `README.md` |
| 实现进度（checkbox 完成度） | OpenSpec `tasks.md` |
| ID 分配与定位 | `tasks/` 目录结构（`INDEX.md` 是派生索引） |
| branch、dirty、HEAD | Git 实时状态 |

暂缓项与阻塞原因写 README 的验证记录小节，不另起状态文件。
