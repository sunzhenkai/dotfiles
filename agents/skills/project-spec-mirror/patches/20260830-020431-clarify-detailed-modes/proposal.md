# 澄清详细模式并持久化重要范围

- target: agents/skills/project-spec-mirror
- patch: 20260830-020431-clarify-detailed-modes
- risk: high
- status: proposed

## Intent

修复 detailed 三档边界含混和不可验证承诺：

- `complete` 保证所有 inventory 文件有归属与说明，并深入行为承载符号；不再承诺静态工具无法证明的“所有方法零遗漏”。
- `important` 保持全范围文件简述，但只对显式选择的重要路径写深；选择保存到 `important_paths`，后续 update 不再重新猜测。
- `lightweight` 明确为“架构/领域详细、代码文件轻量”，避免被理解为 concise 的别名。
- 用户要求“每个函数/变量”时先确认真实目标；局部变量清单不作为 spec 镜像默认产物。
- important 路径不再自动触发 `notes/`，热点详注仍保持独立 opt-in。

本轮保留现有 `detail_level` 字段及三个枚举，避免连续引入状态迁移；不改投影、图表、热点数量和单项目约束。

## Conflict check

- 现有 `important` 要求工具方法不得漏列，超出正则/AST 候选工具可证明范围；改为覆盖行为承载符号，并要求遗漏风险写明证据。
- 现有状态没有记录哪些路径按 important 写深；新增 `important_paths` 与 `set-sync --important-path`。
- 现有 maintain 把“重要文件”与建立 `notes/` 混在一起；改为两个独立维度。
- 现有 phrase-based contract test 固化“不得漏列”措辞；改成验证 important 路径持久化和“候选而非完备证明”的语义。
- `mode/detail_level` 状态生命周期沿用上一 patch，不发生字段重命名。

## Rationale

文件覆盖可以通过 inventory 确定性核对，但跨语言方法全集无法由当前 `symbols` 提取器可靠证明。把详细度约束放在“行为承载符号”上，并持久化 important 路径，既保留可读性和更新稳定性，也避免模型为满足绝对措辞而制造虚假的完备性。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 更新 detailed 工作流、完成命令和 maintain 语义。
- `agents/skills/project-spec-mirror/references/modes.md` — 重写三档边界、方法覆盖与触发规则。
- `agents/skills/project-spec-mirror/references/layout.md` — 记录 `important_paths` 状态字段。
- `agents/skills/project-spec-mirror/scripts/specctl.py` — 保存、校验 important 路径并在 built 门禁中要求明确选择。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 更新详细模式验收。
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 从短语锁定改为语义契约。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 覆盖 important 路径持久化和门禁。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- important build 无路径应失败，提供路径后应写入状态并通过 validate。
- 检查生产内容不再承诺方法零遗漏，且不把 important 路径等同于热点 notes。
