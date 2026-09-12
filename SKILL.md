---
name: dotf-repo
description: 使用本 dotfiles 仓库管理开发环境：通过 dotf CLI 安装/配置/诊断模块，同步 Agent 运行时（skills、MCP、全局指令），并遵循仓库的开发与测试约定。当 agent 需要在当前机器上装工具、配环境、跑 doctor、同步 agent 能力，或在本仓库提交改动时加载。
---

# 使用 Dotfiles 仓库

本仓库是一套模块化 dotfiles 系统。agent 通过 `dotf` CLI 操作环境，不要手写安装脚本或手改已安装配置。

## 环境操作（优先路径）

一切环境变更走 `dotf`，先 dry-run 再执行：

```shell
dotf <module...> -i|-c|-d|-ic|-icd     # 安装 / 配置 / 诊断
dotf <module...> --dry-run             # 只看计划，不执行（含跨 OS 预览）
dotf <module...> --uninstall|--deconfig  # 卸载 / 撤回 owned 配置
dotf init [--os <id>] [--profile <name>] [--dry-run] [--yes]  # 新机初始化
dotf status [--profile <name>]         # 只读 L0 状态
dotf retry                             # 重试最近 failed 动作
dotf -a --dry-run                      # 全量预览
```

关键语义：

- 没有 update 动词；对已有动作再跑一次即 re-apply。
- `--uninstall` 只适用于 `modules.yaml` 声明且带 `uninstall.sh` 的模块。
- 默认计划确认；非 TTY 且无 `--yes`/`--dry-run` 会快速失败——agent 场景用 `--dry-run` 预览后 `--yes` 执行。
- 模块清单、分组与依赖见仓库根 `modules.yaml`；profile 见 `profiles.yaml`。

## Agent 运行时同步

```shell
dotf agents -ic                     # 装 agent CLI 工具包 + 同步 skills/MCP/全局指令
dotf agents -d --json               # 深度诊断（JSON 报告）
dotf agents skill apply <id>        # 启用一条 Skill（写 overlay 并 sync）
dotf agents skill remove <id>       # 停用并 prune owned 目标
dotf agents mcp apply <id> --tool cursor
dotf agents mcp remove <id> --all-tools
dotf skills -i <group|skill>        # 按组装第三方 skill
```

注意：

- Skill 真相源是编目 `agents/skills.yaml`（按 group 组织，编目内即全量安装）；overlay 在 `agents/skills.lock.yaml`。
- 安装产物（`~/.agents/AGENTS.md`、各 vendor 配置）不要手改，改了会被 `dotf agents --doctor` 判漂移。
- Skill 源仓库位置约定：`.agents/skills/` 项目级、`agents/skills/` 公开共享源，见 `AGENTS.md`。

## 仓库开发

- 代码布局：`src/dotf_cli`、`src/dotf_core`、`src/dotf_tui`、`src/agents`；模块 Handler 在 `scripts/modules/<name>/`。
- 常用校验：`make registry validate`、`make test`、`make shellcheck`、`make templates`、`make ci`。
- 术语与领域模型以 `CONTEXT.md` 为准；开发/issue 流程约定见 `AGENTS.md` 与 `docs/agents/`。
