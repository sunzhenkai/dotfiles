# Dotfiles

Personal dotfiles managed with symlinks.

应用配置位于 `config/<category>/`（shell / editors / terminals / multiplexers / desktop / tools）。
模块能力与路径见仓库根 `modules.yaml`。

## Quick Start

```shell
# clone
git clone git@github.com:sunzhenkai/dotfiles.git ~/.config/dotfiles

# 按 OS profile 完整初始化（系统包 + 可装 + 可配）
dotf init

# 或全量装+配（不含系统包分发步骤）
dotf -a

# 按模块操作（主体优先）
dotf sdk -i          # 安装 SDK
dotf nvim zsh -c     # 配置 nvim & zsh
dotf agents -ic      # 先安装后配置
```

## Usage

```
dotf <module...> -i|-c|-ic
dotf -i|-c|-ic              # 交互选择
dotf -i -a | -c -a | -a     # 全量（按当前 OS 过滤）
dotf init [--os <id>] [--list]
dotf pull | -h

Commands:
  init              OS profile 初始化（系统包 + 可装 + 可配）
  pull              Pull latest updates (with stash protection)

Actions:
  -i                Install
  -c                Apply config symlinks
  -ic               Install then config (stop on install failure)
  -a                Install all + config all
  -h                Show help

Examples:
  dotf pull              # update dotfiles repo
  dotf init --list       # list OS profiles
  dotf -i                # interactive install
  dotf sdk golang -i     # install specific modules
  dotf nvim -c           # config nvim
  dotf -c                # interactive config
  dotf -a                # full setup (install + config)
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
dotf agents -i                 # 安装 agent CLI 工具包（claude/cursor/opencode/codex/kimi-code）
dotf agents -c                 # 同步 skills + MCP
dotf agents -c --doctor        # 同步后输出诊断摘要
python3 scripts/agents/doctor.py
python3 scripts/agents/doctor.py --json --verbose
scripts/agents/sync.sh all --dry-run
```

- 源码：`agents/{skills,commands,vendors,env}`（skills/commands + 工具专属 vendors + MCP/env 真相源）
- 脚本：单一包 `scripts/agents/`（`sync.sh` / `doctor.py` / `env_sync.py`）
- 工具专属路径：`agents/vendors/{claude,cursor,opencode,codex,kimi-code}/`

详见 `agents/README.md`、`agents/env/README.md`。

## ColorScheme

- [rose pine](https://rosepinetheme.com/)
