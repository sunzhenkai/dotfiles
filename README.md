# Dotfiles

Personal dotfiles managed with symlinks.

## Quick Start

```shell
# clone
git clone git@github.com:sunzhenkai/dotfiles.git ~/.config/dotfiles

# install tools + apply configs
dotf -a

# or step by step
dotf -i sdk          # install SDK
dotf -c nvim zsh     # config nvim & zsh
```

## Usage

```
dotf <command|option> [args...]

Commands:
  pull              Pull latest updates (with stash protection)

Options:
  -i [modules...]   Install tools/SDKs
  -c [modules...]   Apply config symlinks
  -a                Install all + config all
  -h                Show help

Examples:
  dotf pull              # update dotfiles repo
  dotf -i                # interactive install
  dotf -i sdk golang     # install specific modules
  dotf -c nvim           # config nvim
  dotf -c                # interactive config
  dotf -a                # full setup
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
dotf -i agents                 # 安装 agent CLI 工具包（cursor/codex/kimi-code）
dotf -c agents                 # 同步 skills + MCP
dotf -c agents --doctor        # 同步后输出诊断摘要
python3 scripts/agents/doctor.py
python3 scripts/agents/doctor.py --json --verbose
scripts/agents/sync.sh all --dry-run
```

- 源码：`agents/`（skills/commands）+ `agent-env/`（MCP/env 真相源，由统一 CLI 调用）
- 兼容：`dotf -c agent-env` 仍可用，但会提示迁移到 `agents`

详见 `agents/README.md`、`agent-env/README.md`。

## ColorScheme

- [rose pine](https://rosepinetheme.com/)
