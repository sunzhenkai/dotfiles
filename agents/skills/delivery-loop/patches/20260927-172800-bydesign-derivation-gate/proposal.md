# Stage 8 增「设计内」驳回推导门

- target: agents/skills/delivery-loop
- mode: update
- patch: 20260927-172800-bydesign-derivation-gate
- risk: medium
- status: proposed

## Intent

真实失败：评审把「控件高度不一致」「弹窗输入偏高」两条用户发现先后驳回为「已修复 / 设计内两档密度」，而一致性验证全绿。复核发现根因不是规则缺失，而是归因流程存在无门的驳回出口——任何 finding 都可以用「这是有意的设计」免检通过，且全绿的契约测试会给这个驳回提供假信心（测试钉住 token 值、契约断言控件跟 token 走，验证的都是「实现符合实现自己」，设计决策本身永远验不到）。

要改变的行为：

1. loop-protocol.md Stage 8 归因表后新增两条硬规则：
   - 把 finding 驳回为「设计内 / not a bug」MUST 附决策推导（设计文档、token 注释、比例依据等可追溯记录）；拿不出推导时 MUST 按 acceptance gap 处理（补验收标准再复验），MUST NOT 维持驳回。
   - 验证全绿 MUST NOT 构成设计正确性证据；一致性契约只能证明「实现符合约定」。评审驳回用户或角色 finding 前必须先问「这个约定本身怎么来的」。
2. evals/cases.yaml 新增 deterministic 用例：驳回「设计内」必须带推导，无推导按 acceptance gap 处理。

非目标：不改三类归因的定义与处置；不改 Stage 7 评审调用方式；不引入第四类归因（该失败本就是 acceptance gap 的子形态，补的是执行门，不是新分类）。

## Conflict check

- 与归因表「acceptance gap = 验收标准漏项」一致：无推导的「设计内」正是「验收标准没问决策来源」这一漏项的表现，归入 acceptance gap 顺理成章。
- 与 role-based-reviewer design.md 61/62 条（分档需推导、禁遗留值升格）互补：那两条管 UI 尺寸档位这一个域，本 patch 把「驳回需推导」上升为 loop 级纪律，覆盖所有 finding。
- 通用性：不出现项目名、控件、像素；「驳回出口无门」是可跨域复用的流程缺陷。

## Rationale

闭环最容易漏的不是「没验证」，而是「验证了错误的对象」。一致性验证越完善，循环论证越牢固，评审者越倾向相信全绿。把驳回出口加上推导门，成本一句追问，收益是拦截整类「围绕现状倒推分类」的伪设计决策。

## Files

- `agents/skills/delivery-loop/references/loop-protocol.md` — Stage 8 末尾追加两条规则
- `agents/skills/delivery-loop/evals/cases.yaml` — 新增用例

## Validation

- 应用前：`git apply --check --recount agents/skills/delivery-loop/patches/20260927-172800-bydesign-derivation-gate/change.patch`。
- 应用后：`git diff --check`；diff 与 proposal 一致；cases.yaml 可解析；无项目专有名词 / 本机路径 / 凭据。
- 本轮源自真实失败（用户两次追问才纠正误判），medium 门禁视同已确认，应用后补 `result.md`。
