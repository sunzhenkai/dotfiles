# Evaluate — 归因自检（2026-09-27）

对照现有行为验证，非文案完整性检查。

> 本记录中的 `SKILL.md` / `loop-protocol.md` 均指生产稿路径
> `agents/skills/delivery-loop/SKILL.md` 与 `references/loop-protocol.md`。
> promote 后本目录的候选正文副本已删除（见 decision.md），评估对象即已晋升的生产内容。

## 回归（现有成功路径是否被打断）

| 检查 | 结果 |
|---|---|
| 三类归因表（skill gap / implementation bug / acceptance gap）仍在 | PASS |
| Stage 8 驳回门（前一轮 patch）仍在 | PASS |
| 增量验证协议（前一轮 patch）仍在 | PASS |
| Stage 9「每切片最多两轮修复」上限未被改动 | PASS |
| Stop conditions 段落未改动 | PASS |
| SKILL.md 主循环 12 步完整、编号连续 | PASS |
| 硬边界「不自动 commit / push / 部署 / 改线上数据」未改动 | PASS |
| 依赖清单、benchmark 隔离语义未改动 | PASS |

结论：改动为 Stage 8 段尾**追加**（loop-protocol 净增 406 字符）+ SKILL.md 第 10 步**追加一句引用**，未删改任何既有行。

## 模式（原失败路径按新指令能否避免）

原失败链：同一 finding 先被驳回为「设计内」→ 改口为「验证缺口」只补测试 → 第三次才到真根因 → 修完未追问泛化。

| 原失败环节 | 新指令覆盖 | 判定 |
|---|---|---|
| 第一次解释不稳时继续推进 | 自检 1「出现第二种解释 MUST 停下重做归因，MUST NOT 沿新解释直接改交付仓」 | 覆盖 |
| 表层修复冒充深层修复 | 自检 2「补验证 vs 补设计决策依据，只在验证层修 MUST 记录未补深层」 | 覆盖 |
| 修完就收工 | 自检 3「收敛后 MUST 追问一次泛化性；不追问不得标记收敛」 | 覆盖 |
| 规则只在 reference、主循环看不到 | SKILL.md 第 10 步直接引用自检锚点 | 覆盖 |

## 契约（skill 自带测试）

- `evals/cases.yaml` 存在，含 5 条 deterministic 用例（既有 4 条 + 前轮 bydesign 1 条）。
- 本轮候选稿**不新增 eval case**：三条自检规则是流程强制步骤，判定对象是「编排者是否执行了自检」，无法在无运行态的 deterministic case 里伪造；如强行补 case 会变成文案自证。此项记为**未覆盖**，不编造分数。
- 静态门 `check-quality-gates.sh` 当前 PASS（含前两轮 patch 的 reverse 校验）；本轮未改门脚本。

## 副作用（触发范围 / 权限 / 安全）

| 维度 | 判定 |
|---|---|
| 触发范围 | 未变——description 与「复杂门」判定未改 |
| 权限 | 未扩大——未新增任何授权、未放宽硬边界 |
| 破坏性操作 | 未涉及 |
| 密钥 / 凭据处理 | 未涉及 |
| 新增停顿点 | Stage 8 增加一个「解释翻新即停」的检查点；属流程成本，非权限变化 |

## 过拟合扫描

扫描范围：候选 `loop-protocol.md` / `SKILL.md` / `proposal.yaml`。
关键词：机器路径、固定像素值、产品代号、示例数据标识、项目专有页面名。

结论：**零泄漏**。两处疑似命中经核实为误报——`/tmp/` 是生产稿原有的 `evidence_root` 占位符（相对化示例写法），`taskflow` 是本 skill 声明的依赖项名及 `agents/skills/taskflow` 路径片段，均非本轮引入。

## 结论

`pass`

三条规则为可执行强制步骤（MUST + 明确触发条件 + 明确后果），无模糊措辞；回归项全绿，副作用可控，过拟合零命中。契约项因本类规则无法 deterministic 化而记为未覆盖，非失败。
