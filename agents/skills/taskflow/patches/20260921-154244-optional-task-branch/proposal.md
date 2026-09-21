# 统一切分支策略：可选切；干净从默认分支最新代码切；dirty 提示处理

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-154244-optional-task-branch
- risk: medium
- status: proposed

## Intent

把准备段切任务分支策略统一为三条：

1. 切任务分支是**可选项**，只对涉及面角色为 `必须` 的仓有意义；不切则直接在当前分支实施。
2. 选择切且工作树**干净**：先同步（fetch）默认分支，再从其最新提交 `git switch -c` 创建任务分支；分支已存在则 `git switch`。
3. 工作树 **dirty**：列出未提交路径并提示用户先处理（提交、stash 或清理），处理完再重试。

非目标：不改动 checkbox 进度真相、一轮结束三条件、并行纪律、stock 委托契约；不规定任务分支命名；不引入脚本或第二份账本。

## Conflict check

- 取代现行「必须仓强制切 + dirty 分档（`openspec/changes/{task}-*` 免问直接切 / 其它路径确认带走）」（历史 patch `20260828-223920-confirm-dirty-carry-branch`、`20260828-231347-dirty-task-skip-ask`）。dirty 新规则一律提示处理，不再自动携带，属用户明确要求的统一。
- fail closed 底线保留：仍禁止自动 stash / reset / 强制切换，新增禁止携带未提交改动直接 checkout。
- Driver 协议为逐字固定文本：本轮改的是模板本身，脚手架抄写规则不变。
- `evals/cases.yaml` 同步更新 `driver-protocol-verbatim`、`propose-tasks-skeleton`、`fail-closed-must-repos`；其余 case 不受影响。
- 并行表中「准备段切分支必须串行」保留：选择切时仍串行。

## Rationale

规则从「强制 + 两档 dirty 特判」收敛为「可选 + 干净/脏两档」，更机械可执行：干净有确定命令序列（fetch → 基于默认分支最新提交建分支），dirty 交还用户处理，消除路径白名单判断。可验证：eval 用确定性期望覆盖三档行为与禁区。

## Files

- `agents/skills/taskflow/SKILL.md`：涉及面表角色说明、Driver 协议切分支条目、propose 骨架 1.1、纪律「涉及面与交付分支」小节
- `agents/skills/taskflow/evals/cases.yaml`：更新上述三个 case 的期望

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；frontmatter `name` 仍为 `taskflow`；Driver 协议模板与纪律段措辞一致；`evals/cases.yaml` 仍为合法 YAML（python yaml.safe_load）
