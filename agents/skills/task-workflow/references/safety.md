# task-workflow 安全契约

只保留会造成错误写入、进度丢失或错误结案的硬规则；阶段步骤见其他 reference。测试是 case 细节的 SSOT，末列只给代表用例；改规则必须同步改测试。

| ID | 触发条件 | 必须行为 | 回归测试 |
|----|----------|----------|----------|
| RES-1 | 本条或本会话已有唯一 `TNNNN` / task 路径 | 显式传给 `resolve`，不得丢掉焦点改走启发式 | `test_resolve_by_id` |
| RES-2 | 只有 status / 时间等启发式候选 | 返回 `needs_confirm`，确认前不写 task | `test_infer_heuristic_needs_confirm` |
| RES-3 | apply 显式命中 archived task | apply 意图允许报告后 `restore`；其他命令不得静默恢复 | `test_resolve_reports_archived_match_and_restore` |
| PLAN-1 | new / explore / design / propose | 不为 task 分支运行 fetch/status/checkout/worktree；工作上下文保持尚未准备 | `test_planning_commands_are_thin_and_git_free` |
| CHECKOUT-1 | apply 准备仓库 | 只处理涉及面角色=必须；不把 cwd、`.`、建议仓或排除仓自动加入 | `test_prepare_branches_from_task_skips_unrelated_and_cwd` |
| CHECKOUT-2 | 已记录 checkout 或 task 分支被 worktree 持有 | 续用真实 checkout，并只持久化准备成功的 binding | `test_prepare_branches_reuses_recorded_worktree_and_persists` |
| CHECKOUT-3 | origin fetch 失败，或非目标分支存在 dirty | fail closed 并等用户处理，禁止自动 stash/reset/force checkout。dirty 先按变更路径归属分类：全部落在 canonical planning root 内记 `dirty_role=planning` 并给出可继续动作，其余（含混合与无法判定）按 delivery 阻断 | `test_prepare_branches_blocks_dirty` |
| CHECKOUT-4 | execution/archive 使用 delivery checkout | binding 必须存在、同源、非 detached HEAD 且 branch 匹配；不得用 canonical checkout 隐式替代 | `test_execution_context_requires_binding_for_must_checkout` |
| APPLY-1 | implementing/blocked/testing/done transition | 顶层 outcome 优先；只允许 `references/apply.md` 表中六种 result；`next` 或任一 target 仍有 remaining 时禁止 testing/done | `test_advance_blocked_precedes_candidates_and_testing_rejects_remaining` |
| APPLY-2 | candidate 可能依赖 deferred 项，或仅有 change 级前置依赖 | Agent 先检查 checkbox 直接/传递依赖；exact defer 只针对当前 checkbox 且 reason 写 blocker identity；不批量 defer 同 change 其余项或后续 change 的独立项 | `test_deferred_dependency_chain_keeps_independent_candidate` |
| APPLY-3 | archived/missing OpenSpec 或重复 checkbox 文本 | 不猜测调度；返回 deferred/error 并保留原文 | `test_advance_rejects_duplicate_remaining_checkbox_text` |
| APPLY-4 | testing/done/archive 使用验证证据 | remaining 非空禁止 testing；仓级回归不是 final verification；dirty 证据仅 provisional；实现恢复或 branch/HEAD 变化使 final snapshot stale | `test_worktree_apply_advance_archive_lifecycle` |
| APPLY-5 | apply 暂停类 outcome、`next` 或对外完成声明 | 只有 `done` 可宣称完成并桥接 archive；`next` 继续独立项且已 defer 项并行挂起；暂停类 outcome 停本轮调度并保持 `in_progress`；`next_action.forbidden` 列出的动作本轮一律不做 | `test_apply_pause_outcomes_are_not_completion` |
| APPLY-6 | apply 中断后续作 | 只从 `execution-context` 的 `resume` 取事实；`in_flight` 不得当作未开始重做，`unknown` 必须报告并等确认；binding 齐全时不得重跑 `prepare-branches` | `test_execution_context_resume_reports_in_flight_item` |
| APPLY-7 | implementing 期间的调度节奏 | 首轮批量 exact defer 不可执行项；只跑 targeted 验证，全仓回归留到 testing；已记账 checkbox 不重复审阅；`budget.should_report` 为 true 时先汇报再继续 | `test_apply_rhythm_rules_are_pinned` |
| DELEG-1 | apply 委托子 agent 或并发评审 | 不得无限等待、不得因委托失败判 blocked、不得让委托成为 candidate 必经路径；具体墙钟与失败次数上限是 `apply.md` 的节奏建议，不在本表 | `test_delegation_budget_rules_are_pinned` |
| PROXY-1 | 关联 OpenSpec 的仓不是 `spec-driven` schema，或 change 位于独立 store | 以 `unsupported_openspec_schema` / `unsupported_openspec_store` 具名失败并停止；不猜测 artifact 结构，不把失败推迟到 apply | `test_unsupported_openspec_schema_is_named_explicitly` |
| PROXY-2 | 委托任何 `openspec-*` skill | 必须在该 target 的 canonical `planning_root` 下执行且显式传 change name，二者缺一不得委托；propose 收尾与 archive 外部动作前先跑 `openspec validate --strict --change <name>` | `test_openspec_delegation_contract_is_pinned_in_references` |
| DATA-1 | INDEX 与 task 目录漂移或 identity 冲突 | 合并扫描分配 ID；可修复漏行，有冲突/缺路径时 mutation fail closed | `test_catalog_omitted_row_is_repaired_and_id_not_reused` |
| DATA-2 | scope/work-context/OpenSpec/acceptance 是操作数据 | malformed/未知 role/缺验收结构/非空 store 带行号失败，不猜默认 | `test_malformed_work_context_and_openspec_tables_report_lines` |
| ARCH-1 | archive 进入任何外部写入前 | dry-run 先校验 catalog/tables/target/delivery binding+branch+status，把 active-complete 列为 pending action；不得执行外部 mutation | `test_archive_initial_preflight_lists_active_complete_without_mutation` |
| ARCH-2 | target 已部分归档或 final preflight 重跑 | 按 active/uniquely_archived/archived_incomplete/missing/ambiguous 分类，归档识别用 `YYYY-MM-DD-<change>` 整名匹配；已唯一归档标 completed，missing/ambiguous/status unavailable 不可覆盖 | `test_archive_multi_target_partial_retry_recognizes_completed_target` |
| ARCH-3 | remaining、unchecked acceptance、missing/stale verification 或 exact dirty delivery | 未授权时统一 code 2 + affected + exact_action；授权仅覆盖对应条件并写 `## Gate Overrides` | `test_archive_confirmations_are_code_2_and_gate_overrides_are_audited` |
| ARCH-4 | external archive/design 后进入 final preflight | 要求 target 已归档且 changes.md 存在；新 dirty/branch/HEAD/verification 变化在 movement 前阻断；只保留四类精确 flags | `test_archive_final_preflight_reports_new_dirty_and_keeps_task_active` |
| MUT-1 | new/advance/archive/restore 主 mutation 失败 | 尝试全部 rollback；成功则恢复调用前状态，失败则返回 primary_error、rollback_errors、affected_paths、recovery_hint | `test_advance_reports_structured_rollback_failure` |

## 仓库角色

| role | 来源 | 约束 |
|------|------|------|
| delivery | 必须仓、工作上下文 checkout | apply 准备；archive 必须 valid、同源、clean |
| planning | OpenSpec canonical planning root | 校验并读写 change artifacts；dirty 只诊断 |
| task_store | 保存 tasks/INDEX 的工作区仓 | 依靠锁和回滚；dirty 只诊断 |
| reference | 建议/排除仓 | 不切分支、不检查状态 |

同仓多角色时 delivery 优先。工作区 `.` 仅在工作区自身确为必须修改仓时才是 delivery。

## 状态所有权

README 保存 task 身份、status、计划涉及面与真实工作上下文；`tasks/INDEX.md` 保存 ID 分配与定位（mutation 前由 task 目录对账）；OpenSpec `tasks.md` 保存 checkbox 完成事实；`.task-apply-state.json` 保存 deferred 身份与原因；`progress.md` 保存阶段、验证文本与 clean delivery branch/HEAD final snapshot；Git 保存 branch、worktree、dirty、HEAD 实时事实。

不得增加第二份完成度、deferred 或 checkout 真相源。
