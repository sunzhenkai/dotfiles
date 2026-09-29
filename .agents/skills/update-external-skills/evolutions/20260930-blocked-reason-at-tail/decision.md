# decision — 20260930-blocked-reason-at-tail

**promote**（2026-09-30）

## 晋升前核对（三项均满足）

- **用户确认**：本轮先展示 Evolution Proposal YAML，并就范围（只改正文 / 正文 + 改
  `lock_update.py` / 转去啃下发成本）征询，用户选定「正文 + 改 `lock_update.py`」；
  候选稿与代码 diff 展示后，用户明确选择 promote。
- **Evaluate 为 pass**：见 `eval.md`。回归（真实 9 source dry-run，exit=0，未写锁，
  `keep` / `wrote` 行格式不变）、模式（阻断原因落在输出最后 30 行内，原故障场景
  零补取上游）、契约（`tests/test_lock_update.py` 12 passed；全量 711 passed / 1 failed，
  唯一失败已定性为与本轮无关的既有环境漂移；`make registry validate` 通过）、
  副作用（frontmatter 逐字节未动，触发范围未变，未扩权限，无新增写操作）四项通过。
- **改动与 Proposal 一致，无夹带**：候选稿与生产稿 diff 共 19 行增删，全部落在
  第 1 步、第 2 步、坑实录标题与新增坑 16；坑 1–15、收尾、下一步、边界各段逐行未动。

## 落地内容

正文（生产稿 `.agents/skills/update-external-skills/SKILL.md`）：

- 第 1 步命令改为 `tee` 到本轮日志后挑读，明写不要截断实时输出。
- 第 1 步新增 `blocked>0` 处置分支：读输出末尾的合并报告定性，对照坑 11 判断是否
  过宽规则误报；明写不要为定性另建 ad-hoc clone、不要重跑第 1 步。
- 完成标准由 `blocked=0` 改为 `blocked=M`，并说明 M>0 是合法结局。
- 第 2 步补「输出一次读全，挑读用 grep 不用 tail」。
- 新增坑 16，记录结构性根因（stdout 是唯一载体 + checkout 用完即删）与已修部分。

仓库工具（随本轮一并落地在工作区，未提交）：

- `src/agents/lock_update.py`：`AuditBlocked` 携带 `findings`；新增纯函数
  `blocking_findings`（`[BLOCK]` 行 + 紧随命中行，每 skill 上限 8 条，无 marker 时
  回退到输出尾部）与 `report_blocked`（最多列 5 个 skill）；`update_lock` 在所有
  source 处理完、`wrote` 行之前打合并报告。
- `tests/test_lock_update.py`：5 个新用例，其中端到端用例以「被阻断 source 排在前、
  干净 source 排在后」断言报告位置，防止后人把报告挪回 `keep` 行旁而静默退化。

## 知情取舍

报告回显审计命中行原文，`hardcoded_secret` 的命中行理论上可能含真密钥。这些行今天
已由 `_audit_skill` 的 `print(output)` 全量打进同一份 stdout，本轮未扩大 stdout
暴露面，但末尾位置更容易被读进上下文并转述。用户在看清该取舍后仍选择直接 promote
（未要求脱敏），理由与 eval 一致：命中行原文是判断误报的唯一依据，脱敏会削弱定性能力。
若日后要求脱敏，改点在 `blocking_findings` 的 evidence 分支，属独立一轮。

## 晋升后动作

- 项目级 skill（`.agents/skills/`）由仓库直接加载，本会话即时生效；
  `~/.agents` / `~/.claude` / `~/.kiro` 无本 skill 副本，无需安装通道同步。
- **未代为 `dotf agents -c`、未 commit、未 push**（坑 15 与正文收尾规则）。
- 需提醒用户：本机存在自动 `git add` 的 hook，本轮 4 个文件已进入 index
  （`src/agents/lock_update.py`、`tests/test_lock_update.py`、本目录候选稿与
  proposal.yaml），`eval.md` 与本 `decision.md` 视 hook 触发时机可能为 untracked。
  提交前请先 `git status` 确认带走的是哪些文件。

## 遗留（不属本轮）

- `tests/test_audit_skill.py::test_ssh_senv_and_config_mentions_are_not_credential_paths`
  既有失败：仓库已无 first-party 审计脚本副本，用例回退到本机受管副本，而副本仍缺
  `~/.ssh/senv` 排除。下发刷新受管副本后需单独复核；若届时仍失败，说明该精度修复
  在 first-party → solo-skills 迁移中丢失，须按坑 11 去 solo-skills 补。
- 下发成本（正文「边界」所指 `acquire_all` 取回策略与 `dotf agents` 子集入口）
  本轮未碰。注：仓库已有提交将第三方拉取改为按 revision 去重 + 缓存 + 稀疏拉取，
  实际下发耗时需重新测量后再判断是否还有独立任务可做。
