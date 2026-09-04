# Dotfiles

Personal dotfiles deployed with explicit copy/merge/render strategies and allowlisted read-only symlinks.

应用配置位于 `config/<category>/`（shell / editors / terminals / multiplexers / desktop / tools）。
模块能力与路径见仓库根 `modules.yaml`。

## Quick Start

```shell
# clone
git clone git@github.com:sunzhenkai/dotfiles.git ~/.config/dotfiles

# 新机：最小 bootstrap（不读 modules.yaml；缺 PyYAML 时引导安装）
bash scripts/bootstrap.sh --check-only
bash scripts/bootstrap.sh            # 就绪后委托 dotf init

# 或直接按 OS + 使用场景初始化（默认 profile=full）
dotf init --list                     # OS profile 与使用场景 profile
dotf init --dry-run                  # 先看计划
dotf init --profile minimal --yes    # 最小环境
dotf init --yes                      # 非交互全量

# 状态与重试
dotf status --profile remote         # 只读 L0
dotf retry                           # 重试最近失败动作

# 全量装+配（不含 doctor）
dotf -a --dry-run

# 按模块操作（主体优先）
dotf sdk -i --dry-run    # 预览计划
dotf nvim zsh -c --yes   # 非交互配置
dotf agents -ic
```

## Profiles

使用场景 profile（`profiles.yaml`，与 OS 正交）：

| Profile | 含义 |
|---------|------|
| `minimal` | system/sdk/git/zsh/starship |
| `remote` | minimal + nvim/tmux/cli 工具/agents |
| `desktop` | minimal + 终端/桌面模块（按 OS 过滤） |
| `full` | 当前 OS 适用全集（默认） |

模块清单与分组见 `modules.yaml`（`group` / `depends_on`）。
AI Agent 按分组初始化提示词见 [`Dotfiles.md`](./Dotfiles.md)。

## Usage

```
dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd
dotf -i|-c|-d|...                 # 交互选择（按 group 展示）
dotf -i -a | -c -a | -d -a | -a   # 全量（按当前 OS 过滤；单独 -a 不含 doctor）
dotf init [--os <id>] [--profile <name>] [--yes] [--dry-run] [--list]
dotf status [--profile <name>] [--json]
dotf retry
dotf pull | -h

Commands:
  init              OS + 使用场景 profile 初始化（统一 planner）
  status            只读 L0 环境状态
  retry             重试最近报告中的 failed 动作
  pull              Pull latest updates (with stash protection)

Actions / controls:
  -i/-c/-d          Install / config / doctor
  -a                Install all + config all
  --dry-run         Show plan only (cross-OS preview is dry-run only)
  --continue-on-error
                    After failure, run only dependency-independent actions; final exit stays nonzero
  --yes / -y        Skip plan + side-effect confirms (not validation/backup)
  --json            Redacted execution summary JSON
  --deep            Enable doctor L1
  -h                Show help

Confirm model:
  Plan confirm before execute (default N); no per-module install/config prompts after.
  Side-effect confirms remain for changing default shell and Docker install/config.
  Non-TTY without --yes/--dry-run fails fast.

Examples:
  dotf pull
  dotf init --list
  dotf init --profile remote --dry-run
  dotf status --profile minimal
  dotf sdk golang -i --dry-run
  dotf nvim -c --yes
  dotf -d -a --dry-run
```

## Workflow

- Local
  - Ghostty / Wezterm
  - zsh + Starship
  - Neovim
- Remote
  - Tmux / Herdr / Zellij
  - Neovim

## Agents（统一入口）

skills、MCP/profiles 与 doctor 已收敛为单一对外模块 `agents`：

```shell
dotf agents -i                 # 展开为各 agent CLI 的独立 install
dotf cursor -i                 # 仅安装 Cursor CLI
dotf cursor -c                 # 仅 vendor 配置（不隐式 sync）
dotf agents -c                 # 聚合同步 skills（~/.agents/skills）+ MCP
dotf agents -c --tool cursor   # 过滤同步（仅 MCP/env；skills 与 tool 无关）
dotf agents -d --deep --json   # L0 + L1 深度诊断（脱敏 JSON）
scripts/agents/sync.sh all --dry-run
```

- 源码：`agents/{skills,skills-defaults.yaml,vendors,env}`（一手 skills + 第三方默认清单 + 工具专属 vendors + MCP/env 真相源）
- 脚本：单一包 `scripts/agents/`（`sync.sh` / `doctor.py` / `env_sync.py`）
- 工具专属路径：`agents/vendors/{cursor,kiro,opencode,codex,kimi-code,pi}/`

详见 `agents/README.md`、`agents/env/README.md`。

## ColorScheme

- [rose pine](https://rosepinetheme.com/)

## 配置状态边界与恢复

`modules.yaml` 为每个配置模块声明 `copy` / `merge` / `render` / 只读 `symlink` 策略。可写配置安装到 HOME 的真实文件或目录；应用产生的 cache、session、plugin、credential 与本机路径不会回写仓库。因为 `copy` 不会随仓库编辑自动变化，修改 `config/` 后必须重新运行 `dotf <module> -c`；可先用 `--dry-run` 查看计划，doctor 会把未应用的源变化报告为 `changed`。

升级旧安装时，先运行 `dotf <module> -c --dry-run`。指向本仓声明源的历史整目录软链会在执行时仅 unlink 链接本身，再创建 HOME 真实目录并复制受管内容；仓库源不会被移动或删除。外来软链、未托管真实目标、受管后被本机修改的文件默认是 `conflict`，不会静默覆盖或删除。dotf 只 reconcile managed manifest 明确拥有且 hash 未被本机修改的条目；冲突应先审查，必要时保留统一备份后再显式处理。

本机 Agent/Codex 覆盖只放在 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/`：

```shell
PYTHONPATH=scripts python3 -m dotf_core.overlays init     # 新机创建外置安全示例
PYTHONPATH=scripts python3 -m dotf_core.overlays migrate  # 迁移旧仓库 local 配置
```

默认 Agent profile 是低风险 `research`，不会启用 browser；`browser` / `full` 必须显式选择。普通 `dotf agents -c` 只写 HOME 与 XDG state，不反写仓库模板。维护者修改 `agents/env/` 后需显式生成并审查模板：

```shell
python3 scripts/agents/generate_templates.py
# CI 使用同一命令后执行 git diff --exit-code
```

执行状态写入 `${XDG_STATE_HOME:-$HOME/.local/state}/dotf/runs/` 的逐动作 journal。事务失败会逆序 rollback；若 rollback 本身失败，保留 `failed-rollback` journal 与备份供人工恢复，不要重新创建可写整目录软链。普通失败可用 `dotf retry`，它会从最近完整摘要选出 failed 动作并重新经过正常 planner/registry/OS 校验。
