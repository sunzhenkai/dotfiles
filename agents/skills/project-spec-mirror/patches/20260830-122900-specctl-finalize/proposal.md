# specctl finalize：把收尾四步并成一条命令

- skill: project-spec-mirror
- risk: medium
- 依据: skill-creator「重复的多步操作写进 scripts/，写一次每次受益」

## 问题

build 与 update 的收尾固定是 `coverage` → `validate` → `set-sync --built ...` → `validate` 四步，
顺序和参数都要 Agent 自己编排。历史 patch 里 `fix-state-lifecycle`、`fix-build-step-number`
都是这类顺序性修复，说明这段编排本身是缺陷来源。

同时现状有一处不对称：`cmd_set_sync` 内部已经在写盘前跑 `validation_issues`，
所以「先 validate 再 set-sync」是重复的；而真正需要门禁的 `coverage`（`enforce` 时
`missing` 必须为空）反而没有内建，全靠 Agent 记得先跑。

## 改动

### specctl.py

- 抽出 `sync_state(spec_root, args)`：原 `cmd_set_sync` 的计算与写盘逻辑原样搬入，
  `cmd_set_sync` 变成「定位 spec_root → `sync_state` → emit」的薄封装，行为不变。
- 新增 `cmd_finalize`：
  1. 用即将生效的 `mode` / `detail_level` / `scope` 预演出 `probe` 状态，据此跑 `collect_coverage`——
     因为 `enforce` 取决于目标粒度，用旧状态算会误判；
  2. `coverage.ok` 为假时停在这一步，返回 `stage=coverage`、`reason=coverage_missing`
     和完整 `missing` 列表，**不写盘**；
  3. 通过后调 `sync_state`（内含骨架校验），再跑一次 `validation_issues` 复验；
  4. 单次 emit 合并输出 coverage 摘要、`issues` 与 `state`，保持 stdout 只有一份 JSON。
- `finalize` 隐含 `--built`（它就是「本轮完成」这个动作），其余参数与 `set-sync` 一致，
  额外接受 `--path` 供 coverage 收窄。set-sync 的参数定义抽成 `add_sync_args` 供两者复用。
- `set-sync` 保留不动，分步排查时仍可用。

### 文档与自检

- SKILL.md：命令表加 `finalize` 行；build 第 11 步与 update 第 7 步改用一条 `finalize`，
  并注明需要分步排查时仍可单独跑三个命令。
- `references/checklist.md`：状态机那条改为「收尾走 finalize；直接用 set-sync 时自己补 coverage 与 validate」。
- `evals/cases.yaml`：`state-lifecycle-finalize` 与 `coverage-file-table-vs-inventory` 两个 case 同步。
- `tests/test_skill_contract.py`：`EXPECTED` 加入 `finalize`。
- `tests/test_specctl.py`：新增 `FinalizeTest` 三例——coverage 未过时阻断且不写盘、
  覆盖达标后记录 commit 并进入 built、非 Git 源 `synced_commit` 保持 `null`。

## 非目标

- 不改 `collect_coverage` 的判定规则，也不改 `validation_issues`。
- 不废弃 `set-sync`、`coverage`、`validate` 任何一个命令。
- 不改变非 Git 源不得伪造 commit 的约束。

## 验证

- `git apply --check --recount`：通过
- 临时副本预跑：`python3 -m unittest discover` → **53 tests OK**（原 50 + 新增 3）
