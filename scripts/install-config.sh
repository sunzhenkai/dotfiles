#!/bin/bash
set -e

DOTFILES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +%s)

# 配置映射：name="source:target"
declare -A CONFIGS=(
  ["starship"]="starship/starship.toml:~/.config/starship.toml"
  ["nvim"]="nvim:~/.config/nvim"
  ["kitty"]="kitty:~/.config/kitty"
  ["tmux"]="tmux:~/.config/tmux"
  ["alacritty"]="alacritty:~/.config/alacritty"
  ["zellij"]="zellij:~/.config/zellij"
  ["ghostty"]="ghostty:~/.config/ghostty"
  ["wezterm"]="wezterm:~/.config/wezterm"
  ["zsh"]="zsh:~/.config/zsh"
  ["yazi"]="yazi:~/.config/yazi"
  ["hypr"]="hypr:~/.config/hypr"
  ["helix"]="helix:~/.config/helix"
  ["shell_gpt"]="shell_gpt:~/.config/shell_gpt"
  ["zed"]="zed:~/.config/zed"
  ["fcitx5"]="fcitx5:~/.config/fcitx5"
  ["git"]="git:~/.config/git"
  ["opencode"]="opencode:~/.config/opencode"
)

# 通用安装函数
install_config() {
  local name="$1"
  local def="${CONFIGS[$name]}"

  if [ -z "$def" ]; then
    echo "Unknown config: $name"
    echo "Available: ${!CONFIGS[*]}"
    exit 1
  fi

  IFS=':' read -r source target <<<"$def"
  target="${target/#\~/$HOME}"
  local expected_link="$DOTFILES_ROOT/$source"

  # 检查是否已经是正确的符号链接
  if [ -L "$target" ]; then
    local current_link
    current_link=$(readlink -f "$target" 2>/dev/null || readlink "$target")
    local expected_abs
    expected_abs=$(readlink -f "$expected_link" 2>/dev/null || echo "$expected_link")
    if [ "$current_link" = "$expected_abs" ]; then
      echo "Already installed: $name"
      return 0
    fi
  fi

  # 备份已存在的文件/目录
  [ -e "$target" ] && mv "$target" "$target-$TIMESTAMP"

  # 创建符号链接
  ln -s "$expected_link" "$target"
  echo "Installed: $name"
}

# 特殊配置：zsh
install_zsh() {
  install_config "zsh"
  if [ -e ~/.zshrc ]; then
    # 内容相同则跳过
    if diff -q "$DOTFILES_ROOT/zsh/zshrc" ~/.zshrc >/dev/null 2>&1; then
      echo "~/.zshrc already up-to-date"
      return
    fi
    mv ~/.zshrc ~/.zshrc-$TIMESTAMP
  fi
  cp "$DOTFILES_ROOT/zsh/zshrc" ~/.zshrc
  echo "Installed: ~/.zshrc"
}

# 特殊配置：git
# install_git() {
#   install_config "git"
#   echo ""
#   echo "⚠️  Add to ~/.gitconfig after [user]:"
#   echo '[include]'
#   echo '    path = ~/.config/git/gitconfig'
# }
#
# # 特殊配置：git-global
# install_git_global() {
#   local expected_link="$DOTFILES_ROOT/git/gitconfig"
#
#   # 检查是否已经是正确的符号链接
#   if [ -L ~/.gitconfig ]; then
#     local current_link
#     current_link=$(readlink -f ~/.gitconfig 2>/dev/null || readlink ~/.gitconfig)
#     local expected_abs
#     expected_abs=$(readlink -f "$expected_link" 2>/dev/null || echo "$expected_link")
#     if [ "$current_link" = "$expected_abs" ]; then
#       echo "Already installed: git-global"
#       return 0
#     fi
#   fi
#
#   [ -e ~/.gitconfig ] && mv ~/.gitconfig ~/.gitconfig-$TIMESTAMP
#   ln -s "$expected_link" ~/.gitconfig
#   echo "Installed: git-global"
# }

# 安装全部
install_all() {
  for name in "${!CONFIGS[@]}"; do
    case "$name" in
    zsh) install_zsh ;;
    # git) install_git ;;
    *) install_config "$name" ;;
    esac
  done
}

# 主函数
main() {
  local config="$1"

  if [ -z "$config" ]; then
    echo "Usage: $0 <config_name|--all>"
    echo ""
    echo "Available configs:"
    for name in $(echo "${!CONFIGS[*]}" | tr ' ' '\n' | sort); do
      echo "  $name"
    done
    echo ""
    echo "Special:"
    echo "  --all, -a     Install all configs"
    echo "  git-global    Overwrite ~/.gitconfig"
    exit 1
  fi

  case "$config" in
  --all | -a) install_all ;;
  zsh) install_zsh ;;
  git) install_git ;;
  git-global) install_git_global ;;
  *) install_config "$config" ;;
  esac
}

main "$@"
