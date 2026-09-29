# eval — 20260930-blocked-reason-at-tail

评估时间：2026-09-30。结论：**pass**。

## 回归（按现有成功路径走一遍，确认没被新规则打断）

- 第 1 步命令语义未变，仍是 `make skills-lock-update`，候选稿只在其外面套了 `tee`；
  Makefile target 与 CLI 参数均未改。
- 完成标准行 `wrote agents/skills.lock.yaml sources=N blocked=M` 格式未变，
  候选稿只把文档里的 `blocked=0` 写成 `blocked=M`（真实输出一直是变量）。
- `keep <id> @ <rev> (<exc>)` 行格式未变；`str(AuditBlocked)` 仍只是短消息，
  findings 挂在属性上、由 `report_blocked` 单独打印。
- 端到端真实 dry-run（`python3 src/agents/lock_update.py --dry-run`，9 个 source）：
  exit=0，333 行输出，7 个 source 报 `current`、1 个 source 被审计阻断，
  与改动前的可观测行为一致。`--dry-run` 未写锁；跑完 `git status` 只有本轮的
  `src/agents/lock_update.py`、`tests/test_lock_update.py` 与 evolutions 目录。
- 无阻断时 `report_blocked` 直接 return，不产生任何新输出（既有 7 个用例覆盖的路径不变）。

## 模式（原先失败/重试的那类问题，按新指令是否能避免）

- 原故障：第 1 步接 `tail -60` → 阻断原因全丢 → 另建 ad-hoc clone + 重跑全树审计
  → 多一次网络与扫描，并留下需手工清理的 /tmp checkout。
- 真实 dry-run 验证：输出的**最后 30 行**内即含完整阻断报告（8 条 `[BLOCK]`，
  各带命中行原文，加 `(11 more blocking findings)` 溢出计数，总数与全量 grep 一致）。
  原故障场景下 `tail -30` 已足够定性，无需任何补取上游。
- 端到端用例 `test_update_lock_reports_block_reasons_at_end_of_run` 用两个 source
  （被阻断的排在前、干净的排在后）断言报告位置：在最后一个 `==> lock-update` 之后、
  `wrote` 行之上。这条断言就是原故障的机械化防线——若有人把报告挪回 `keep` 行旁，
  它会失败（`keep` 行离尾部有数百行）。
- 第 2 步「输出一次读全，挑读用 grep 不用 tail」写进正文，覆盖同模式的低价版本。
- 正文同时明写「不要为定性另建 ad-hoc clone」「不要重跑第 1 步」，
  直接封掉本轮实际走过的两条弯路。

## 契约（目标 skill / 仓库自带测试）

- `python3 -m pytest tests/test_lock_update.py -q` → **12 passed**（7 旧 + 5 新）。
  新用例：`[BLOCK]` 与命中行配对、每 skill 上限与溢出计数、无 marker 时回退到输出尾部、
  `report_blocked` 的最多 5 个 skill 上限、端到端报告位置断言。
- `python3 -m pytest tests/ -q` → **711 passed, 1 failed**。
- 唯一失败 `tests/test_audit_skill.py::test_ssh_senv_and_config_mentions_are_not_credential_paths`
  **与本轮无关，已定性为既有环境漂移**：该用例经 `resolve_audit_script`（本轮未触碰）
  回退到本机受管审计脚本；直接对同一 fixture 跑该安装副本即复现
  `[BLOCK] credential_paths`，不经过任何本轮改动的代码。仓库内已无 first-party
  审计脚本副本（`agents/skills/` 为空），因此该用例的通过与否取决于本机已装脚本版本，
  而本机副本是上一轮下发的产物。用例本身于 2026-09-20 加入。
  不由本轮引入，也不由本轮修复；预期在下一次下发刷新受管副本后需单独复核。
- `make registry validate` → 通过（strict-handlers）。

## 副作用

- **触发范围**：候选稿 frontmatter（`name` / `description`）与生产稿逐字节一致
  （`diff <(head -4 …) <(head -4 …)` 无差异），触发条件未扩大也未缩小。
- **权限与破坏性操作**：未新增任何写操作、未扩权限。代码改动只增加 stdout 行与
  `AuditBlocked.findings` 属性；`UpdateResult.blocked` 仍是 id 元组，
  调用方与既有解析不受影响。
- **输出体积**：新增报告有双上限（每 skill 8 条 `[BLOCK]`、最多列 5 个 skill），
  最坏约 85 行，不会把 tail 窗口里的其他关键行挤出去。
- **候选稿改动面**：与生产稿 diff 共 19 行增删，全部落在第 1 步、第 2 步、
  坑实录标题与新增坑 16；未夹带无关段落重写。
- **密钥暴露面（需用户知情的取舍）**：报告会回显审计命中行的原文，其中
  `hardcoded_secret` 的命中行理论上可能含真密钥。但这些行**今天已经**由
  `_audit_skill` 的 `print(output)` 全量打进同一份 stdout，本轮只是把其中的
  `[BLOCK]` 子集复制到末尾，未扩大 stdout 暴露面。代价是：末尾位置更容易被
  agent 读入上下文并转述。未做脱敏，因为命中行原文正是判断误报的唯一依据
  （本轮就是靠 `const token = preparedCacheDirectories.get(...)` 这行原文
  判定它是标识符而非密钥）。若要求脱敏，需改为截断或掩码，会削弱定性能力。

## 结论

**pass**。回归、模式、契约、副作用四项均通过；唯一的全量测试失败已证明为
与本轮无关的既有环境漂移。密钥暴露面一项是知情取舍，已在晋升请求中向用户点明。
