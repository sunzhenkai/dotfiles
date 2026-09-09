# AGENTS.md

## Skills 目录约定

- `.agents/skills/`（项目级 skill）：用于迭代**本项目**，只在当前仓库内生效。
- `agents/skills/`：用于安装到不同 agent 的**可复用、共享 skill** 源仓库，**不用来迭代本项目**。改动这里的 skill 面向的是各 agent 环境的通用能力，与本项目自身的开发无关。

## 全局 AGENTS.md 安装

- 全局指令源在 `agents/instructions/`（`AGENTS.md` 正文 + `install.yaml` 目标表）；`dotf agents -c` 会安装到 `~/.agents/AGENTS.md`、`~/.codex/AGENTS.md` 与 Cursor 用户级 `~/.cursor/rules/00-dotf-global.mdc`。安装产物不要手改。
- 漂移检查复用同一 instruction planner：`dotf agents --doctor` 的 `instructions` 段，以及 `dotf tui` 的 Status / Conflicts 面板（聚合 `agents:instructions:` 漂移）。不要在消费侧另写近似逻辑。

## Agent skills

### Issue tracker

Issues 与 specs 以 markdown 文件存放在 `.scratch/<feature>/`。详见 `docs/agents/issue-tracker.md`。

### Domain docs

single-context。详见 `docs/agents/domain.md`。
