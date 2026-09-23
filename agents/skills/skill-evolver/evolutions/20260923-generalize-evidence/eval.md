# Eval — 20260923-generalize-evidence

对照生产稿 `agents/skills/skill-evolver/SKILL.md` 验证候选稿，目标 Skill 无测试套件，做指令级对照。

## 回归

- Core Loop（Experience → … → Promote or Reject）各步骤未被改动，成功路径不变。
- 门禁三条、Proposal 先确认、一次一轮等既有硬规则原样保留。
- 改动仅落在「4. Patch Skill」第 4 条与「安全约束」首条之后，无顺手重构。

结论：既有成功路径不被新规则打断。pass

## 模式

原失败场景：记录证据时照抄原始任务细节（内部项目代号、私有 trace 文件名），
写入 proposal.yaml / eval.md / commit message，事后需人工清除。

按新指令重放：第 4 条要求证据「先抽象后落盘」，给出可操作格式
（时间 + 次数 + 事件类型）与示例（「2026-09-23 两次真实委派」），
且适用范围显式含 commit message —— 原先唯一无规则覆盖的产物。

结论：该类问题按新指令可避免。pass

## 契约

无自带测试；指令级核对：新规则是可执行检查（写产物前过一遍抽象步骤），
不含「注意」「尽量」类软措辞。pass

## 副作用

- 触发范围未扩大：仍只在 skill-evolver 流程内生效。
- 权限与破坏性操作无变化；规则只收紧产物内容，不变松任何约束。
- 证据可验证性保留：通用描述仍含时间/次数/事件类型，可追溯。

## 结论

pass。本轮候选 diff 与 proposal.yaml 一致，无夹带编辑。
