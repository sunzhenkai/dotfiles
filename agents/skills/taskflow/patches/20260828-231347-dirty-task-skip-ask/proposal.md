# dirty 仅含当前 task 的 OpenSpec change 时直接切分支

- target: agents/skills/taskflow
- patch: 20260828-231347-dirty-task-skip-ask
- risk: medium
- status: proposed

## Intent

准备段切任务分支时，去掉「dirty 一律列出路径并展开处理选项」的过宽判断。

- 未提交路径全部落在当前 task 的 OpenSpec change（`openspec/changes/{task}-*`，含 driver 与子 change）时，直接 `git switch` / `git switch -c`，不提问。
- 还有其它未提交路径时，只列出路径并确认是否继续 checkout（改动随普通 switch 带走）。
- 确认题不得展开成提交、留在当前分支或其它处理方式。

非目标：不恢复 stash / reset / 强制切换；不按文件类型做白名单；不把实现代码或其它 task 的 change 算作可免问集合。

## Conflict check

- 收窄上一轮「dirty 一律确认带走」：happy path（propose 后未提交的本 task OpenSpec 产物）不再停问；含其它路径时仍须确认。
- 与「禁止 stash / reset / 强制切换」不冲突。
- 与「一轮结束三条件」不冲突：含其它 dirty 且用户未确认仍属需要用户决策。
- Driver 协议仍逐字写入；本轮改的是模板固定文本本身。
- 不引入第二份进度账本，不新增 command。

## Rationale

propose 之后工作树常只含本 task 的 driver 与子 change。把这当成要停下来的 dirty，并给出「留在 main / 先提交 / 其它」选项，是多余判断。前缀规则机械可执行，跨仓仍成立，可用现有 eval 核对。

## Files

- `agents/skills/taskflow/SKILL.md`：Driver 协议固定文本与纪律段切分支规则
- `agents/skills/taskflow/evals/cases.yaml`：更新 `fail-closed-must-repos`

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；frontmatter `name` 仍为 `taskflow`；Driver 协议模板与纪律段一致；`evals/cases.yaml` 仍为合法 YAML
