# 归档 task-grill — 结果

status: applied

## 实际改动

与 `change.patch` 一致：

- 删除 `agents/skills/task-grill/SKILL.md`、`agents/skills/task-grill/agents/openai.yaml`；
- `agents/skills.yaml` dotfiles group 移除 `- task-grill` 编目条目；
- `agents/README.md`「示例条目」段移除 task-grill 介绍；
- `agents/skills/taskflow/SKILL.md` 阶段路由表移除「收敛（可选）」行；
- `agents/skills/task-design/SKILL.md` 移除导语、流程图、「何时不用」表、「相关」段共 4 处引用；
- 保留 `agents/skills/task-grill/patches/` 全部审计记录（含本目录）。

偏差：无。

## 验证

- `git apply --check --recount` 通过；应用后 `git diff --check` 无空白错误；
- `agents/skills.yaml` 可被 yaml 解析；
- 全仓 grep：`task-grill` 仅剩历史 patch 记录（task-design 的 20260828 patch proposal），无悬挂引用；
- 代码侧（src/、scripts/、tests/）无 task-grill 引用；
- `pytest -k "agents or skill"`：187 passed，2 failed——两处失败均为 `wayfinder`/`code-review` 编目注释（用户未提交的在途改动）与本机 overlay `00-local.yaml` 的关联问题，与本次归档无关。

## 后续

- 未执行 commit / push（按协议等待用户要求）。
- 安装产物 `~/.agents/skills/task-grill/`、`~/.kiro/skills/task-grill/` 未动；需用户跑 `dotf agents -c` 重新同步后由安装器清理（是否 prune 以 sync 实现为准）。
