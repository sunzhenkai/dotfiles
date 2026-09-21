# 切分支只针对修改仓；dirty 修改仓三选一（不切直接改 / 带脏切换 / git worktree）

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-155458-modify-repo-branch-options
- risk: medium
- status: proposed

## Intent

在 `20260921-154244-optional-task-branch` 基础上再收敛：

1. 切任务分支只针对**修改仓**（涉及面角色为 `必须` 且真正要改的仓）；task 所在仓不是修改仓时不切分支。
2. 修改仓工作树 **dirty** 时不再是「提示用户先处理」，改为列出未提交路径并给三个选择：
   - 不切分支，直接在当前分支修改
   - 携带未提交改动 `git switch` 切换
   - `git worktree add` 从默认分支最新提交建独立工作树
3. 修改仓**干净**时规则不变：先 fetch 默认分支，再从其最新提交 `git switch -c`（分支已存在则 `git switch`）。

非目标：不改 checkbox 进度真相、一轮结束三条件、并行纪律、stock 委托契约；不规定任务分支命名；不引入脚本。

## Conflict check

- 取代上一轮 dirty 档「提示先处理」与 fail closed 中「禁止携带未提交改动直接 checkout」——带脏切换现为用户的显式选项之一。
- 保留底线：仍禁止自动 stash / reset / 强制切换；用户未选择、git 拒绝或切错仓时停下。
- Driver 协议为逐字固定文本：本轮改的是模板本身，脚手架抄写规则不变。
- `evals/cases.yaml` 更新 `fail-closed-must-repos`；`driver-protocol-verbatim` 与 `propose-tasks-skeleton` 的期望措辞（可选切分支规则 / 可选条目）仍成立，不动。

## Rationale

dirty 不必是阻塞态：不切直接改、带脏切换、worktree 隔离三条路径都安全且可逆，交用户选择比一刀切「先处理」更贴合实际。把切分支限定到修改仓，避免在只承载 task 台账的仓上做无意义分支操作。三个选项与干净档命令均可机械执行、可写确定性 eval。

## Files

- `agents/skills/taskflow/SKILL.md`：Driver 协议切分支条目、propose 骨架 1.1、纪律「涉及面与交付分支」小节
- `agents/skills/taskflow/evals/cases.yaml`：更新 `fail-closed-must-repos`

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；frontmatter `name` 仍为 `taskflow`；Driver 协议模板与纪律段措辞一致；`evals/cases.yaml` 可被 `yaml.safe_load` 加载
