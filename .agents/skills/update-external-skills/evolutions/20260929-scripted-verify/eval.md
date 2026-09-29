# Eval — 20260929-scripted-verify

对照**现有行为**验证候选稿，不看文案完整度。

## 回归（当前成功路径不能被新规则打断）

- 手工流程的产物与脚本输出逐条对齐：`changed` 对本轮真实锁变更给出
  `changed_content=18 changed_revision_only=3 added=1 removed=2`，与手工
  `git diff | grep content_hash` 计得的 18 个 content_hash 变化一致；改名以
  `+delivery-loop / -task-delivery / -task-goal` 成对出现，符合预期语义。
- 第 1、3 步未改动：`make skills-lock-update` 与 `bin/dotf agents -c --yes` 的
  说法、判读表保持原文。
- `make registry validate`（含 src/ 布局护栏）通过：新文件落在 `src/agents/` 包内，
  未违反「src/ 根级只允许包目录 + ensure_pyyaml.py」。
- 仓库全量测试 `make test`：见文末补记。

## 模式（原先要人工逐条判读的，现在是否自动避免）

真实数据上跑通三类此前手工判读：

- 4 个此前手写 clone+tree_hash+diff 的条目：`tree_hash == content_hash: 4/4`，
  并自动报出 `unowned taskflow/experience/failures/archive-skip-specs.md`
  ——正是本轮靠手写 `diff -r` 才发现、且按决策保留未删的那处残留。
- optional 条目：`NOT-INSTALLED archify (outside desired set…)`，不再误报下发失败（坑 9）。
- 纯重钉条目：`verify --ids grilling,domain-modeling,wait-what` → `failures=0`，
  对应坑 8 的「上游只动锁外路径」场景。
- 误输入：`--ids nope` → `not in lock: nope`，exit 1，快速失败不静默。

## 契约（目标 skill 自带测试）

- 项目级 skill（`.agents/skills/`）不被 pytest 收集（`norecursedirs` 含 `.*`），
  新代码的测试按仓库惯例落 `tests/`：`tests/test_agents_lock_verify.py` 9 例全绿，
  覆盖 干净安装 / 未托管残留 / 该在而不在 / 运行残留不计 / optional 出口 /
  hash mismatch / revision-only / 条目增删 / `changed` 走真实 git 仓。
- 测试不打网络：`acquire_all` 经模块级 `_acquire` 间接调用，测试 monkeypatch 该 seam。

## 副作用

- 触发范围未变：frontmatter description 只把「看 content_hash 判断」换成
  「make skills-verify 判断」，「何时用 / 何时不用」与边界段一字未动。
- 权限与破坏性操作：脚本纯读取——不写 lock、不写 layout、不动 manifest；
  删除动作仍由人决定（候选稿明确写「脚本不替你删」）。
- 未删任何既有硬规则：坑 1–11 全部保留，5/6/9 只加「已自动化」注记。

## 已知偏差与踩过的坑（记入坑 14）

- 首版 `lock_verify.py` 用 `from agents.third_party import ThirdPartyLockError`，
  而 `third_party.py` 内部与同目录邻居用扁平 import。`src/agents` 是无 `__init__.py`
  的命名空间包，两种 import 产生两个模块对象、两个异常类，`except ThirdPartyLockError`
  静默漏接，测试里表现为异常穿透到 main。已改为与邻居一致的扁平 import。
- `_finding` 的初版按 `op.state == "missing"` 出标签，实测计划里缺文件是
  `action == "create"`（state 为 `changed`），已按真实计划词汇表修正。

## 结论

pass（待 `make test` 全量绿后确认；候选稿与 Proposal 一致，无夹带编辑）
