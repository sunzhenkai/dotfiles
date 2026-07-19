# Dotfiles

Personal dotfiles managed with symlinks.

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
  --dry-run         Show plan only
  --yes / -y        Skip confirm (not validation/backup)
  --json            Redacted execution summary JSON
  --deep            Enable doctor L1
  -h                Show help

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
  - Tmux / Zellij
  - Neovim

## Agents（统一入口）

skills/commands、MCP/profiles 与 doctor 已收敛为单一对外模块 `agents`：

```shell
dotf agents -i                 # 展开为各 agent CLI 的独立 install
dotf claude -i                 # 仅安装 Claude CLI
dotf cursor -c                 # 仅 vendor 配置（不隐式 sync）
dotf agents -c                 # 聚合同步 skills + MCP
dotf agents -c --tool cursor   # 过滤同步
dotf agents -d --deep --json   # L0 + L1 深度诊断（脱敏 JSON）
scripts/agents/sync.sh all --dry-run
```

- 源码：`agents/{skills,commands,vendors,env}`（skills/commands + 工具专属 vendors + MCP/env 真相源）
- 脚本：单一包 `scripts/agents/`（`sync.sh` / `doctor.py` / `env_sync.py`）
- 工具专属路径：`agents/vendors/{claude,cursor,opencode,codex,kimi-code}/`

详见 `agents/README.md`、`agents/env/README.md`。

## ColorScheme

- [rose pine](https://rosepinetheme.com/)
