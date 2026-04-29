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

## ColorScheme

- [rose pine](https://rosepinetheme.com/)
