# task-workflow 安全契约

本文件只保留会造成错误写入、进度丢失或错误结案的硬规则；阶段步骤见同目录其他 reference。测试是 case 细节的 SSOT。修改规则时必须同步更新对应测试。

| ID | 触发条件 | 必须行为 | 回归测试 |
|----|----------|----------|----------|
| RES-1 | 本条或本会话已有唯一 `TNNNN` / task 路径 | 显式传给 `resolve`，不得丢掉焦点改走启发式 | `test_resolve_by_id`, `test_infer_hint_id` |
| RES-2 | 只有 status / 时间等启发式候选 | 返回 `needs_confirm`，确认前不写 task | `test_infer_heuristic_needs_confirm`, `test_resolve_zero_and_multi` |
| RES-3 | apply 显式命中 archived task | apply 意图允许报告后 `restore`；其他命令不得静默恢复 | `test_resolve_reports_archived_match_and_restore`, `test_restore_rolls_back_move_and_status_when_index_write_fails` |
| PLAN-1 | new / explore / design / propose | 不为 task 分支运行 fetch/status/checkout/worktree；工作上下文保持尚未准备 | `test_planning_commands_are_thin_and_git_free` |
| CHECKOUT-1 | apply 准备仓库 | 只处理涉及面角色=必须；不把 cwd、`.`、建议仓或排除仓自动加入 | `test_prepare_branches_from_task_skips_unrelated_and_cwd`, `test_prepare_branches_from_task_empty_skips` |
| CHECKOUT-2 | 已记录 checkout 或 task 分支被 worktree 持有 | 续用真实 checkout，并只持久化准备成功的 binding | `test_prepare_branches_reuses_recorded_worktree_and_persists`, `test_prepare_branches_multi_repo_persists_only_success_and_returns_blocking` |
| CHECKOUT-3 | origin fetch 失败，或非目标分支存在 dirty | fail closed 并等用户处理；禁止自动 stash/reset/force checkout；不得把 dirty 必须仓标为成功 | `test_prepare_branches_blocks_configured_origin_fetch_failure`, `test_prepare_branches_blocks_dirty`, `test_prepare_branches_parser_has_no_skip_dirty` |
| CHECKOUT-4 | execution/archive 使用 delivery checkout | binding 必须存在、同源、非 detached HEAD 且 branch 匹配；不得用 canonical checkout 隐式替代 | `test_execution_context_requires_binding_for_must_checkout`, `test_execution_context_rejects_wrong_repository_and_detached_head`, `test_archive_rejects_clean_wrong_branch_with_expected_actual` |
| APPLY-1 | implementing/blocked/testing/done transition | 顶层 outcome 优先；只允许 blocked/next/deferred_only/validation_required/validation_recorded/done；`next` 或任一 target 仍有 remaining 时禁止 testing/done | `test_advance_blocked_precedes_candidates_and_testing_rejects_remaining`, `test_advance_defers_resumes_and_keeps_candidate_work`, `test_later_change_gate_defer_keeps_sibling_candidate` |
| APPLY-2 | candidate 可能依赖 deferred 项，或仅有 change 级前置依赖 | Agent 先检查 checkbox 直接/传递依赖；exact defer 只针对当前 checkbox 且 reason 写 blocker identity；不按 change 批量 defer 同 change 其余项或后续 change 的独立项 | `test_deferred_dependency_chain_keeps_independent_candidate`, `test_advance_rejects_defer_that_is_not_an_exact_remaining_item`, `test_later_change_independent_candidate_survives_predecessor_defer`, `test_later_change_gate_defer_keeps_sibling_candidate` |
| APPLY-3 | archived/missing OpenSpec 或重复 checkbox 文本 | 不猜测调度；返回 deferred/error 并保留原文 | `test_restored_task_with_archived_incomplete_change_is_not_done`, `test_advance_rejects_duplicate_remaining_checkbox_text` |
| APPLY-4 | testing/done/archive 使用验证证据 | remaining 非空禁止 testing；仓级回归不是 final verification；dirty 证据仅 provisional；实现恢复或 branch/HEAD 变化使 final snapshot stale | `test_worktree_apply_advance_archive_lifecycle`, `test_later_change_gate_defer_keeps_sibling_candidate` |
| APPLY-5 | apply 暂停类 outcome、`next` 或对外完成声明 | 只有 `done` 可宣称完成并桥接 archive；`next` 继续独立项且已 defer 项并行挂起；`blocked`/`deferred_only`/`validation_required` 停本轮调度并保持 `in_progress` | `test_apply_pause_outcomes_are_not_completion` |
| DATA-1 | INDEX 与 task 目录漂移或 identity 冲突 | 合并扫描分配 ID；可修复漏行，有冲突/缺路径时 mutation fail closed | `test_catalog_omitted_row_is_repaired_and_id_not_reused`, `test_catalog_duplicate_and_active_archive_conflicts_block_mutation`, `test_catalog_reports_dir_identity_and_missing_index_path` |
| DATA-2 | scope/work-context/OpenSpec/acceptance 是操作数据 | malformed/未知 role/缺验收结构/非空 store 带行号失败，不猜默认 | `test_unknown_scope_role_and_malformed_tables_fail_before_git`, `test_malformed_work_context_and_openspec_tables_report_lines`, `test_archive_requires_acceptance_structure`, `test_execution_context_rejects_nonempty_openspec_store` |
| ARCH-1 | archive 进入任何外部写入前 | dry-run 先校验 catalog/tables/target identity+status/delivery binding+branch+status，并把 active-complete 列为 pending action；不得执行外部 mutation | `test_archive_initial_preflight_lists_active_complete_without_mutation`, `test_archive_requires_acceptance_structure`, `test_archive_fails_closed_when_recorded_checkout_is_missing`, `test_archive_fails_closed_when_delivery_status_is_unavailable` |
| ARCH-2 | target 已部分归档或 final preflight 重跑 | 以 active/uniquely_archived/archived_incomplete/missing/ambiguous 分类；已唯一归档项标 completed，missing/ambiguous/status unavailable 不可覆盖 | `test_archive_multi_target_partial_retry_recognizes_completed_target`, `test_archive_rejects_incomplete_archived_openspec`, `test_archive_structural_failures_are_not_overrideable` |
| ARCH-3 | remaining、unchecked acceptance、missing/stale verification 或 exact dirty delivery | 未授权时统一 code 2 + affected + exact_action；授权仅覆盖对应条件并写 `## Gate Overrides` | `test_archive_confirms_any_remaining_with_verbatim_items`, `test_archive_confirmations_are_code_2_and_gate_overrides_are_audited`, `test_archive_blocks_dirty_delivery_and_supports_exact_override` |
| ARCH-4 | external archive/design 后进入 final preflight | 要求 target 已归档且 changes.md 存在；新 dirty/branch/HEAD/verification 变化在 task movement 前阻断；只保留四类精确 flags | `test_archive_final_preflight_reports_new_dirty_and_keeps_task_active`, `test_archive_requires_changes_but_dry_run_can_build_summary_first`, `test_archive_rejects_clean_wrong_branch_with_expected_actual`, `test_archive_parser_has_no_unsafe_flags` |
| MUT-1 | new/advance/archive/restore 主 mutation 失败 | 尝试全部 rollback；成功则恢复调用前状态，失败则返回 primary_error、rollback_errors、affected_paths、recovery_hint | `test_new_reports_structured_rollback_failure`, `test_advance_reports_structured_rollback_failure`, `test_archive_reports_structured_rollback_failure`, `test_restore_rollback_failure_is_structured` |

## 状态所有权

- README：task 身份、status、计划涉及面、真实工作上下文。
- `tasks/INDEX.md`：ID 分配与定位索引；mutation 前由 task 目录对账。
- OpenSpec `tasks.md`：checkbox 完成事实。
- `.task-apply-state.json`：deferred 身份与原因。
- `progress.md`：阶段、验证文本以及 clean delivery branch/HEAD final snapshot；不是新的状态文件。
- Git：branch、worktree、checkout、dirty、HEAD 实时事实。

不得增加第二份完成度、deferred 或 checkout 真相源。
