# task-workflow 安全契约

本文件只保留会造成错误写入、进度丢失或错误结案的硬规则；阶段步骤见同目录其他 reference。测试是 case 细节的 SSOT。修改规则时必须同步更新对应测试。

| ID | 触发条件 | 必须行为 | 回归测试 |
|----|----------|----------|----------|
| RES-1 | 本条或本会话已有唯一 `TNNNN` / task 路径 | 显式传给 `resolve`，不得丢掉焦点改走启发式 | `test_resolve_by_id`, `test_infer_hint_id` |
| RES-2 | 只有 status / 时间等启发式候选 | 返回 `needs_confirm`，确认前不写 task | `test_infer_heuristic_needs_confirm`, `test_resolve_zero_and_multi` |
| RES-3 | apply 显式命中 archived task | apply 意图允许报告后 `restore`；其他命令不得静默恢复 | `test_resolve_reports_archived_match_and_restore`, `test_restore_rolls_back_move_and_status_when_index_write_fails` |
| PLAN-1 | new / explore / design / propose | 不为 task 分支运行 fetch/status/checkout/worktree；工作上下文保持尚未准备 | `test_planning_commands_are_thin_and_git_free` |
| CHECKOUT-1 | apply 准备仓库 | 只处理涉及面角色=必须；不把 cwd、`.`、建议仓或排除仓自动加入 | `test_prepare_branches_from_task_skips_unrelated_and_cwd`, `test_prepare_branches_from_task_empty_skips` |
| CHECKOUT-2 | 已记录 checkout 或 task 分支被 worktree 持有 | 续用真实 checkout，并立即持久化工作上下文 | `test_prepare_branches_reuses_recorded_worktree_and_persists`, `test_worktree_apply_advance_archive_lifecycle` |
| CHECKOUT-3 | origin fetch 失败，或非目标分支存在 dirty | fail closed 并等用户处理；禁止自动 stash/reset/force checkout。已在目标分支可 dirty 续作 | `test_prepare_branches_blocks_configured_origin_fetch_failure`, `test_prepare_branches_blocks_dirty`, `test_prepare_branches_already_on_branch_allows_dirty` |
| APPLY-1 | 每项完成、defer/resume、testing、blocked、done | 用一次 `advance` 原子保存并读取 `result`；`next` 时同轮继续 | `test_advance_persists_state_progress_and_returns_next`, `test_advance_defers_resumes_and_keeps_runnable_work` |
| APPLY-2 | 当前项局部不可执行但仍有 runnable | 保持 checkbox 未勾选并 defer；不得把局部问题升级为全局 blocked | `test_advance_defers_resumes_and_keeps_runnable_work`, `test_advance_rejects_defer_that_is_not_an_exact_remaining_item` |
| APPLY-3 | archived/missing OpenSpec 或重复 checkbox 文本 | 不猜测调度；返回 deferred/error 并保留原文 | `test_restored_task_with_archived_incomplete_change_is_not_done`, `test_advance_rejects_duplicate_remaining_checkbox_text` |
| ARCH-1 | 任一 OpenSpec checkbox 未完成 | 原文返回；由 Agent 说明性质并让用户裁决，CLI 不按 test/healthcheck 关键词分类 | `test_archive_confirms_any_remaining_with_verbatim_items`, `test_archive_does_not_downgrade_gate_for_implementation_wording` |
| ARCH-2 | repository roles 混合或状态异常 | delivery missing/status unavailable/dirty 默认阻断；planning/task_store dirty 仅诊断；delivery 角色优先 | `test_archive_fails_closed_when_recorded_checkout_is_missing`, `test_archive_fails_closed_when_delivery_status_is_unavailable`, `test_archive_allows_dirty_planning_and_task_store`, `test_archive_blocks_dirty_repo_with_delivery_and_planning_roles` |
| ARCH-3 | 用户明确覆盖未完成项或 dirty delivery | 只覆盖被授权项并写入 `changes.md` 审计；不得覆盖 missing/status unavailable | `test_archive_force_merge_allows_remaining`, `test_archive_blocks_dirty_delivery_and_supports_exact_override` |
| MUT-1 | README、INDEX、apply state、progress、审计或目录移动写失败 | 恢复调用前状态；rollback 自身失败必须显式报告 | `test_advance_rolls_back_when_status_index_write_fails`, `test_archive_rolls_back_move_when_index_write_fails`, `test_archive_rolls_back_new_override_audit_file`, `test_restore_reports_rollback_failure` |

## 状态所有权

- README：task 身份、status、计划涉及面、真实工作上下文。
- `tasks/INDEX.md`：ID 分配与定位索引。
- OpenSpec `tasks.md`：checkbox 完成事实。
- `.task-apply-state.json`：deferred 身份与原因。
- `progress.md`：`advance` 生成的阶段、验证证据和快照。
- Git：branch、worktree、checkout、dirty 实时事实。

不得增加第二份完成度、deferred 或 checkout 真相源。
