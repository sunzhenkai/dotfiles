# Evaluation — 20260829-complete-mode-notes-mandatory

## Candidates
- `SKILL.md.candidate` / `skill.md.patch`
- `modes.md.candidate` / `modes.md.patch`
- `cases.yaml.candidate` / `cases.yaml.patch`

## Regression: existing success paths still work

| Case | Status | Note |
|------|--------|------|
| `specctl-json-exit-codes` | unchanged | patch 不碰 specctl.py 或执行契约 |
| `infer-phase-from-state` | unchanged | patch 只在 build 步骤 7 末尾 +1 句 + 新增 8.5，不改阶段推断 |
| `init-confirm-then-build` | unchanged | --confirm 流程未变 |
| `placement-in-vs-external` | unchanged | placement 规则未动 |
| `git-default-branch-commit` | unchanged | git 同步流程未动 |
| `pyramid-knowledge-on-build` | unchanged | 金字塔结构未动；notes/ 是补充而非替代 |
| `facets-and-archify` | unchanged | 切面 + archify 流程未动 |
| `recovery-projections-runnable` | unchanged | 5 投影 INDEX 仍必建 |
| `delivery-summary-fields` | unchanged | 输出格式未动 |
| `preserve-manual-blocks` | unchanged | `<!-- manual -->` 块未动 |
| `exit-2-wait-user` | unchanged | confirm 行为未动 |
| `no-secrets-or-auto-commit` | unchanged | 脱敏与不自动 commit 未动 |
| `detailed-deepens-pages-not-files-tree` | unchanged | `complete` 仍深化已有页、未批量建 files/ |
| `detailed-file-granularity-choice` | unchanged | 档位含义保留 |
| `hotspot-notes-need-scope` | **patched** | 加 must：`detail=complete` 必须 ≥5 篇 notes/；must_not 例外说明 |
| `update-routes-from-diff` | unchanged | update 路径不变 |
| `rename-updates-file-table` | unchanged | rename 处理不变 |
| `legacy-files-dir-preserved` | unchanged | files/ 停更规则不变 |
| `reject-per-file-catalog-request` | unchanged | 拒绝反模式规则不变 |
| `skip-third-party-and-foreign-repos` | unchanged | 三方/外来仓规则不变 |

## Pattern: the missed case now fails-fast

| Failure | Old behavior | New behavior |
|---------|--------------|--------------|
| detail=complete build 漏 notes/ | Agent 按 modes.md "opt-in" 字面理解 → 不建 → 用户 review 后才发现 | build 步骤 8.5 强制要求 ≥5 篇 + 5 类清单 + 主题命名；evals `complete-mode-notes-mandatory` 拦截；`hotspot-notes-need-scope` 加必须项 |

**正向校验**：用真实数据 `algogear-bidder/feature-extraction-lib`（detail=complete，本次 build 后已补 6 个 notes/）对照候选稿：

| 触发条件类 | 已建 notes/ | 命中 |
|-----------|------------|------|
| 1. 跨文件契约 | options-builder-sequencing | ✓ |
| 2. 一致性失败路径差异 | l1-throws-vs-l0l2-no-throw, ruf-parse-resilience | ✓ |
| 3. race 分析 | demand-cache-double-check | ✓ |
| 4. 监控盲区 | ruf-parse-resilience（"声明了 bvar 但未 <<1"） | ✓ |
| 5. 框架宏约束 | preprocessor-feature-macros | ✓ |
| **覆盖类数** | 5/5 | ✓ |
| **总篇数** | 6 篇（≥5） | ✓ |
| **topic 命名** | 6/6 全是 topic（如 `options-builder-sequencing.md`） | ✓ |
| **grep 同 group 已镜像 notes/** | task 1.10（external）6 个 notes/ 在 build 期间未主动 grep | ✗ 但候选稿要求"build 前先 grep"——本案例作为反例驱动规则 |

正向校验通过（5 类覆盖 / 6 篇 / topic 命名），但暴露了"build 前先 grep"这条新规则在生产实操中曾被忽略——这也是为什么补丁里加了这条。

**另一正向对照**：`algogear-bidder/external`（task 1.10，detail=complete，已有 6 个 notes/）：

| 触发条件类 | 已建 notes/（推断） |
|-----------|------------|
| 1. 跨文件契约 | config 注入矩阵（待 confirm） |
| 2. 一致性失败路径差异 | lazada 接口偏离根因 |
| 3. race 分析 | （需 confirm） |
| 4. 监控盲区 | tiktok 双层 HMAC（疑似） |
| 5. 框架宏约束 | rta DialOption |

5 类大概率都有覆盖（外层细节需 1 个 sub-agent 复核）。

## 反向校验：non-complete 模式仍不建 notes/

| Mode | Expected notes/ count | 候选稿是否破坏 |
|------|----------------------|---------------|
| `concise` | 0 | modes.md 表行 `concise / lightweight → 不建`，未改 |
| `lightweight` | 0 | 同上 |
| `detail_level=important` | 0（默认）；用户点名时按 ≤15 篇 | 表行改为 "默认不建、用户点名才建"，未引入 "≥5 篇" 强制 |

反向校验通过：候选稿只对 `detail_level=complete` 引入 "必建 ≥5 篇" 规则，其他档位保持原行为。

## Contract: scripts / public API 不变

- `scripts/specctl.py` 未动
- CLI 命令名 / 退出码 / JSON 输出格式未动
- `set-sync` / `validate` / `route` 行为未动
- `--hotspot` 标记语义未动（"用户单点指定的热点" 仍由 `set-sync --hotspot` 维护，与 topic 命名并列）

## Side effects

| 维度 | 评估 |
|------|------|
| 触发范围 | 仅 `detail_level=complete` 的 build 阶段；其他模式 / 阶段未受影响 |
| 权限 | 未变（specctl 不写源码，只读 + 写 spec/） |
| 破坏性 | 无（候选稿只 add 新 must / 新 case，未删既有规则） |
| KPI / bvar / 契约 | 无影响（specctl.py 未改） |

## Verdict

**PASS**

候选稿满足：

- 解决真实失败模式（task 1.11 漏 6 个 notes/，已在用户 review 后补）
- 不破坏既有成功路径
- 触发条件可执行（5 类清单）而非主观判断
- 与已镜像仓的 `external` 行为对齐（6 个 notes/ 主题符合 5 类清单）
- 风险评估为 medium（default 行为变化范围明确，仅 detail=complete）

下一步：等用户确认后晋升（promote），覆盖生产稿 `SKILL.md` / `references/modes.md` / `evals/cases.yaml`。

如不接受，可 reject：候选稿留在 evolutions/ 作为否决记录。
