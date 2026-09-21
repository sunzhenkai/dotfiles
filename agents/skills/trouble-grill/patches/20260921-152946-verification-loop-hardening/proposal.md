# 把「验证」内嵌进排查循环，堵住未经验证的结论

- target: agents/skills/trouble-grill
- mode: update
- patch: 20260921-152946-verification-loop-hardening
- risk: medium
- status: proposed

## Intent

强化 trouble-grill 对「归因到未经验证的结论」的防护，用户已逐条批准以下改动：

1. 假设板新增必填字段「预测 + 验证动作」：每个 open 假设必须带可观察预测（若成立则应观察到 Y）与获取它的具体动作；写不出预测的假设须 sharpen 或丢弃；验证动作超过一轮未执行的假设不许留板。
2. 明确状态转换条件：open → confirmed 须过四道门且证据达 fact/strong；open → ruled-out 须有反证数据并写明依据。
3. 新增措辞规范：未坐实的假设全程带等级标签（如「[weak] 缓存穿透」），只有 confirmed 才允许写「根因是 X」。
4. 新增证据等级升级路径（guess→weak→strong→fact 各级的典型升级动作）。
5. Gate 3 补反事实判据（固定其他变量、只改疑似原因）。
6. 公开性：业务例子（TopOn/TradPlus/campaign_id 等）替换为虚构通用场景；落盘位置中的 OpenViking 机器特例软化为「有持久记忆工具则同步」。
7. 去重：根因门槛单点定义（并入 confirmed 状态转换条件），收口规则引用而不复述；「可证伪」在锚点定义，Gate 4 引用。
8. 正文新增不适用场景：单步可复现、报错直接指向原因的问题直接修，不上板；frontmatter description 同步补触发边界。

非目标：不改 skill 的整体结构（锚点→假设板→门禁→检查→收口→落盘）与排查语义；不加自进化目录；不改 agents/openai.yaml。

## Conflict check

- 落盘段点名 task-explore：task-explore 同在 `agents/skills/` 共享仓内，符合公开性约束，保留。
- 与 `diagnosing-bugs`（不在本仓）职责不同（反馈环建设 vs 归因纪律），无冲突。
- 其余：none。

## Rationale

原稿把「验证」集中在收口门禁（Gate 1-4），排查循环本身没有强制验证机制，agent 可带 guess 走到收口才被拦；`confirmed` 状态无进入条件，铁律悬空；跨轮对话中「最可能方向」悄悄升级为结论无语言级约束。改动把验证动作内嵌进假设板数据结构、给状态机加转换条件、加措辞规范，均为通用、可执行、可观察的行为规则。改动内容已逐条经用户批准。

## Files

- `agents/skills/trouble-grill/SKILL.md`：上述 8 项正文改动（唯一改动文件）。

## Validation

- 应用前：`git apply --check --recount`。
- 应用后：`git diff --check -- agents/skills/trouble-grill`；核对 frontmatter 合法、`name` 与目录名一致；通读成品确认无隐私/业务信息（TopOn、TradPlus、campaign_id 等已清除）、无重复定义；目标 skill 无自带测试（not-available）。
