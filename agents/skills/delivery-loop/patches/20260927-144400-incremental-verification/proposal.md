# 增量验证协议：变更→门禁映射、证据复用、checkpoint

- target: agents/skills/delivery-loop
- mode: update
- patch: 20260927-144400-incremental-verification
- risk: medium
- status: proposed

## Intent

闭环慢的两个结构性原因：每轮修复都重跑全量测试与全量截图矩阵；耗时步骤（截图矩阵、全量套件）没有 checkpoint，被中断后状态无法回填，只能整轮重来。要在 loop-protocol 里制度化增量验证，既不损失功能与效果，也不为「安心」重复跑无关检查（Stage 10 已有此精神，缺可执行协议）。

要改变的行为：

1. loop-protocol.md 新增「增量验证协议」一节，含四条规则：
   - 变更→门禁映射：切片开工前声明触碰面（模块 / 路由 / 组件 / UI surface），只跑映射到的门禁；全量验证只在 Stage 10 跑一次。
   - 证据复用：截图与日志按 (surface, state, viewport, theme) 键写入 evidence manifest；复跑时未受影响的键直接引用既有产物，不重新生成。
   - fail-fast 顺序：静态门 → 目标单测 → 浏览器/运行态契约 → 截图矩阵；前一层红了不跑后一层。
   - 可中断步骤 checkpoint：每个耗时步骤先把结果落盘（manifest / 日志）再汇总；任何时刻被中断，已完成的键可直接用于回填任务状态，不整轮作废。
2. SKILL.md 主循环第 11 步补「先重跑受影响检查」的协议指针（已有语义，加链接固化）。
3. evals/cases.yaml 新增 deterministic 边界用例：局部样式修复不触发全量截图矩阵重生成、复用 manifest 既有键。

非目标：不改 Stage 1–10 的顺序与停止条件；不改 benchmark 隔离；不把增量验证用于跳过 Stage 10 全链路。

## Conflict check

- 与 Stage 10「不为安心重复跑全量」一致：本 patch 把该精神前移到每一轮修复，且明确全量仍跑一次，不削弱完成标准。
- 与 Stage 6 证据要求一致：复用只针对「未受影响的键」，受影响键必须重新生成，证据完整性不降级。
- 通用性：规则不出现具体测试框架、项目结构或路径，以「门禁 / 键 / manifest」抽象表述。

## Rationale

慢的根源不是单点耗时，而是「变更与验证之间没有映射、证据与表面之间没有键控」。补上这两张索引后，增量修复的验证开销与改动面成正比；checkpoint 让长步骤可中断、可续传，闭环对执行环境（会话中断、委派超时）的鲁棒性提高。可机械检查：本轮验证清单是否只含映射内门禁、manifest 中未受影响键是否复用。

## Files

- `agents/skills/delivery-loop/references/loop-protocol.md` — 新增「增量验证协议」一节
- `agents/skills/delivery-loop/SKILL.md` — 第 11 步固化协议指针
- `agents/skills/delivery-loop/evals/cases.yaml` — 新增用例

## Validation

- 应用前：`git apply --check --recount agents/skills/delivery-loop/patches/20260927-144400-incremental-verification/change.patch`。
- 应用后：`git diff --check`；diff 与 proposal 一致；cases.yaml 仍为合法 YAML；无项目专有名词 / 本机路径 / 凭据。
- 本轮经 delivery-loop 目标显式授权（用户指出「过程太慢，分析优化」），medium 门禁视同已确认，应用后补 `result.md`。
