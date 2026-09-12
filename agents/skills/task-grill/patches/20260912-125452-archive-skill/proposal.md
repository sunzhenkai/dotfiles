# 归档 task-grill

## 意图

从共享 Skill 真相源 `agents/skills/` 归档（删除）`task-grill`：

- 删除 `agents/skills/task-grill/` 全部生产内容（`SKILL.md`、`agents/openai.yaml`），保留 `patches/` 审计记录。
- 从编目 `agents/skills.yaml` 的 `dotfiles` group 移除 `task-grill` 条目，使其不再被 `dotf agents -c` 安装。
- 清理三处下游引用，避免指向已删除 skill 的悬挂链接：
  - `agents/README.md`「示例条目」段；
  - `agents/skills/taskflow/SKILL.md` 阶段路由表的「收敛（可选）」行；
  - `agents/skills/task-design/SKILL.md` 的导语、流程图、「何时不用」表与「相关」段。

非目标：不改 taskflow / task-design 的其他行为；不动 `~/.agents/skills/`、`~/.kiro/skills/` 等安装产物（由用户重新 sync 清理）；不删除本 patch 目录与历史 `patches/` 记录。

## 前置判断

- **意图**：归档唯一目标 skill，范围明确。
- **冲突**：与 `taskflow`、`task-design` 的引用是依赖方向（它们指向本 skill），归档后必须同步清理，否则产生悬挂引用；已在改动内处理。与 `pwd-skill-manager` 的 patch 协议不冲突（沿用 `3e763cc` 移除 dotf-ui-design 的先例：删生产、留 patches）。
- **合理性**：skill 由 git 历史保留，可恢复；编目与目录同时移除保持一致性。

## 风险

high（删除能力）。用户已点名归档 task-grill，视为已通过门禁。

## 验证

- `git apply --check --recount` 通过；
- 应用后 `git diff --check`；
- 全仓 grep 确认无残留 `task-grill` 引用（历史 patch 目录与 `.agents/` 同步镜像除外）；
- 相关 pytest 通过。
