# 切分支时 dirty 须确认带走，不再一刀切停下

- target: agents/skills/taskflow
- patch: 20260828-223920-confirm-dirty-carry-branch
- risk: high
- status: proposed

## Intent

准备段切任务分支时：无分支用 `git switch -c`，已有用 `git switch`；禁止 stash / reset / 强制切换。工作树 dirty 时列出未提交路径，问用户是否把改动带到目标分支，未确认或 git 拒绝才停下。

触发：propose 之后工作树常含本任务 OpenSpec 产物，现行「dirty 一律停」会挡住 happy path。

非目标：不按路径白名单自行判定可带走的文件；不把 fetch 失败当作切分支硬停；不把切分支提前到 `taskflow-new`；不要求先把 OpenSpec 提交到默认分支。

## Conflict check

- 与「禁止 stash / reset / 强制切换」不冲突：确认后仍只用普通 `switch` / `switch -c`。
- 与「一轮结束三条件」不冲突：未确认属于需要用户决策。
- 与 Driver 协议逐字写入不冲突：本轮改的是模板固定文本本身，脚手架仍逐字抄写。
- 不引入第二份进度账本，不新增 command。

## Rationale

dirty 是切分支时要问的状态，不是失败。用户确认后带走全部未提交改动；卫生检查交给确认和随后的提交步骤，不在协议里做路径分类。跨仓仍成立，可用现有 eval 核对。

## Files

- `agents/skills/taskflow/SKILL.md`：Driver 协议固定文本与纪律段切分支规则
- `agents/skills/taskflow/evals/cases.yaml`：更新 `fail-closed-must-repos`

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；frontmatter `name` 仍为 `taskflow`；Driver 协议模板与纪律段一致；`evals/cases.yaml` 仍为合法 YAML
