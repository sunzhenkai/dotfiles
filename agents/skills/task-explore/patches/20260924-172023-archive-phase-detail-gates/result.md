# Result

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-172023-archive-phase-detail-gates
- risk: medium
- status: applied
- applied-at: 2026-09-24T17:30:27+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m pytest agents/skills/task-explore/tests -q` → 33 passed（应用前该文件 6 failed / 13 passed）
- privacy check: pass（无个人标识、无绝对路径、示例为占位符）
- mode check: pass（`update`，未夹带 examples/evals/experience）
- 未触及历史 `patches/`、`.agents/skills/`、agent 镜像；新增仅 `references/phase-archive.md` 与本 patch 目录

## Notes

相对 proposal 的三处扩展，均因用户在 `git apply` 前逐轮追加要求，在同一轮 patch 内完成（proposed 阶段允许修正 `change.patch`）：

1. **proposal 列为非目标的「批量归档」已实现**：改为「逐个跑完整门禁 + 门禁结果合并成一次确认」，冲突与门禁不过的任务先剔除不阻塞其余，中途失败即停且已搬的不回滚 —— 与 handoff 批量交接语义对称。
2. **`save` 由建议升级为门禁（第 6 条）**：置于目标路径冲突检查之后，保住「冲突即零副作用」不变量；曾 `handed-off` 的任务必须落盘，纯 `ongoing` 用户坚持可跳过并注明。
3. **新增 `{taskRoot}/SUMMARY.md`（proposal 未含）**：归档时产出给人读的时间线总结，≤40 行、`YYYY-MM-DD — 做了什么 → 得到什么结论` 为主干、含「交付」段（driver 进度与落地位置）、素材读不到写「未记录」不编造；写完先给用户过眼再搬，`reopen` 后再归档则续写而非重写。`TASK.md` 的归档小节只留结论指针，叙述归 SUMMARY，避免两份真相。

SKILL.md 的 archive 段因此从 proposal 里的四条硬门禁增至五条，并在 `## 布局` 树中登记 `SUMMARY.md`。测试新增 14 个用例（archive 门禁 12 + handoff 不归档 1 + 顺序不变量 1），总数 19 → 33；`test_archive_checks_dest_before_mutating_task_md` 改读 reference 并扩展为 dest < save 门禁 < status < move 的四段顺序锁。

未做（留给后续，若需要另起 patch 或 openspec change）：新门禁尚未提升进 `openspec/specs/task-explore-lifecycle/spec.md`；`reopen` 阶段仍无细则文件。未执行 `dotf agents -c`（按 pwd-skill-manager 约定不自动 sync）。
