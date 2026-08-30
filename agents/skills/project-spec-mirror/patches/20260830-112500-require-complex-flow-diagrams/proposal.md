# 复杂业务逻辑必须配图

- target: agents/skills/project-spec-mirror
- patch: 20260830-112500-require-complex-flow-diagrams
- risk: medium
- status: proposed

## Intent

改变「何时画」：复杂业务逻辑（分叉、补偿、状态机、跨模块时序、非平凡数据路径）在 build 中必须交付 archify HTML，并链回对应 `flows/` 页。overview 点名的主处理线凡属此类，不得只靠列表交差。

仍省略线性三步和一张表已说清的步骤。用户点名的图仍然本轮交付。不恢复「凡候选必画、未画即阻塞一切」的旧策略。禁止假 HTML 与 INDEX 占位。archify 不可用时把必配图列为未完成，不声称这些逻辑已经讲清。

不改 Skill 触发条件，不把结构/部署装饰图变成全量必画。

## Conflict check

与 `20260830-020904-adaptive-workload-policy` 部分相逆：那次把图改成「用户点名才交付」，导致核心业务图过少。本次收窄反转范围——只强制复杂业务逻辑，不强制所有候选。

与 archify 委托、禁止手绘冒充、禁止拷贝 schema 的边界无冲突。`specctl validate` 仍不检查 HTML 是否存在；完备性由 Agent 自检与 eval 约束。

## Rationale

读者跟一条有分叉或跨模块的处理线时，列表会丢角色、状态和时序。这类图是理解项目的必要证据，不是装饰。规则可执行：处理线页能否链到已存在的 `.html`；线性 CRUD 仍可省略。跨项目成立。

## Files

- `agents/skills/project-spec-mirror/references/diagrams.md` — 重写何时画
- `agents/skills/project-spec-mirror/SKILL.md` — build 第 6 步与新门禁对齐
- `agents/skills/project-spec-mirror/references/knowledge.md` — 处理线与结束自检要求链图
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 锁定新门禁、去掉「没有图不算失败」
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 更新 facets-and-archify

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
