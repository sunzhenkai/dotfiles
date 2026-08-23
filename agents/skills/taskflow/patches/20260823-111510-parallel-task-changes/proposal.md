# 独立 task / 子 change 优先并行

- target: agents/skills/taskflow
- patch: 20260823-111510-parallel-task-changes
- risk: medium
- status: proposed

## Intent

有多 agent / 子代理能力时，apply `{task}-driver` 对**无未完成依赖、范围不重叠**的单位优先并行：一层是独立子 change `{task}-<slice>`，一层是同一 change 内独立 checkbox（task）。没有该能力则主会话串行。

非目标：不新增 command；不改 Driver 协议固定文本；不另建进度账本；不对有依赖、同工作树可能重叠、准备切分支或收尾段条目并行；不把子代理失败当成整轮结束。

## Conflict check

- 与「进度只有 checkbox」不冲突：并行只改执行方式，完成度仍只认 checkbox；driver 编排项仍由主会话在子 change 全勾且 `validate --strict` 通过后勾。
- 与委托契约不冲突：每个子代理仍须绑定 planning root 与 change name，不发明等价命令。
- 与 Driver 协议逐字写入不冲突：本轮不改 `proposal.md` 模板。
- 与 `task-workflow` 不混用：只约束 taskflow 的 apply 执行，不引入 `tasks/` 台账。

## Rationale

多 slice 的 taskflow 在 apply 阶段最容易被主会话串行拖慢；把「独立则并行、依赖则串行」写成可执行纪律，跨仓库仍成立，且可用 eval case 核对。

## Files

- `agents/skills/taskflow/SKILL.md`：description 补一句触发提示；纪律下新增「并行执行」
- `agents/skills/taskflow/evals/cases.yaml`：新增 `parallel-independent-units` case

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；按 `evals/cases.yaml` 核对新 case 与既有 core/failure case 未被改写
