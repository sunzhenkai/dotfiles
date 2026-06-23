#!/bin/bash
# dotfiles 配置安装脚本（兼容 Bash 3.2+）
set -e

DOTFILES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +%s)
BACKUP_DIR="$HOME/.config/backups"

# ============================================================
# 配置映射函数（兼容 Bash 3.2，不使用关联数组）
# ============================================================

# 获取配置定义 "source:target"，未知名称返回非零
get_config_def() {
  case "$1" in
  starship)  echo "starship/starship.toml:~/.config/starship.toml" ;;
  nvim)      echo "nvim:~/.config/nvim" ;;
  kitty)     echo "kitty:~/.config/kitty" ;;
  k9s)       echo "k9s:~/.config/k9s" ;;
  tmux)      echo "tmux:~/.config/tmux" ;;
  alacritty) echo "alacritty:~/.config/alacritty" ;;
  zellij)    echo "zellij:~/.config/zellij" ;;
  ghostty)   echo "ghostty:~/.config/ghostty" ;;
  wezterm)   echo "wezterm:~/.config/wezterm" ;;
  zsh)       echo "zsh:~/.config/zsh" ;;
  yazi)      echo "yazi:~/.config/yazi" ;;
  hypr)      echo "hypr:~/.config/hypr" ;;
  helix)     echo "helix:~/.config/helix" ;;
  shell_gpt) echo "shell_gpt:~/.config/shell_gpt" ;;
  zed)       echo "zed:~/.config/zed" ;;
  fcitx5)    echo "fcitx5:~/.config/fcitx5" ;;
  git)       echo "git:~/.config/git" ;;
  opencode)  echo "opencode:~/.config/opencode" ;;
   claude)    echo "claude:~/.config/claude" ;;
   codex)     echo "codex/config.toml:~/.codex/config.toml" ;;
   cursor)    echo "cursor/mcp.json:~/.cursor/mcp.json" ;;
  logseq)    echo "logseq:~/.logseq" ;;
  iterm2)    echo "iterm2:~/.config/iterm2" ;;
  *)         return 1 ;;
  esac
}

# 获取配置描述
get_config_desc() {
  case "$1" in
  starship)  echo "Starship 终端提示符配置" ;;
  nvim)      echo "Neovim 编辑器配置" ;;
  kitty)     echo "Kitty 终端模拟器配置" ;;
  k9s)       echo "K9s Kubernetes CLI 配置" ;;
  tmux)      echo "Tmux 终端复用器配置" ;;
  alacritty) echo "Alacritty 终端模拟器配置" ;;
  zellij)    echo "Zellij 终端复用器配置" ;;
  ghostty)   echo "Ghostty 终端模拟器配置" ;;
  wezterm)   echo "WezTerm 终端模拟器配置" ;;
  zsh)       echo "Zsh shell 配置" ;;
  yazi)      echo "Yazi 文件管理器配置" ;;
  hypr)      echo "Hyprland 窗口管理器配置" ;;
  helix)     echo "Helix 编辑器配置" ;;
  shell_gpt) echo "Shell-GPT 配置" ;;
  zed)       echo "Zed 编辑器配置" ;;
  fcitx5)    echo "Fcitx5 输入法配置" ;;
  git)       echo "Git 版本控制配置" ;;
  opencode)  echo "OpenCode 配置" ;;
   claude)    echo "Claude Code 配置" ;;
   codex)     echo "Codex CLI 配置（智谱 GLM）" ;;
   cursor)    echo "Cursor 编辑器 MCP 配置" ;;
  logseq)    echo "Logseq 笔记配置" ;;
  iterm2)    echo "iTerm2 终端模拟器配置" ;;
  *)         echo "$1" ;;
  esac
}

# 获取所有配置名（排序后，空格分隔）
get_all_config_names() {
  echo "alacritty claude codex cursor fcitx5 ghostty git helix hypr iterm2 k9s kitty logseq nvim opencode shell_gpt starship tmux wezterm yazi zed zellij zsh"
}

# ============================================================
# 备份与安装
# ============================================================

backup_to() {
  local src="$1"
  local basename
  basename=$(basename "$src")
  local dest="$BACKUP_DIR/${basename}-${TIMESTAMP}"
  mkdir -p "$BACKUP_DIR"
  mv "$src" "$dest"
  echo "已备份 $basename 到 $dest"
}

install_config() {
  local name="$1"
  local def
  def=$(get_config_def "$name") || {
    echo "未知配置: $name"
    echo "可用配置: $(get_all_config_names)"
    return 1
  }

  IFS=':' read -r source target <<<"$def"
  target="${target/#\~/$HOME}"
  local expected_link="$DOTFILES_ROOT/$source"
  local expected_abs
  expected_abs=$(readlink -f "$expected_link" 2>/dev/null || echo "$expected_link")

  # 状态 1: 目标已是正确 symlink → 跳过
  if [ -L "$target" ]; then
    local current_link
    current_link=$(readlink -f "$target" 2>/dev/null || readlink "$target")
    if [ "$current_link" = "$expected_abs" ]; then
      echo "已安装: $name"
      return 0
    fi
    # 状态 2: symlink 指向错误位置且目标存在（非 broken）→ 备份后覆盖
    if [ -e "$target" ]; then
      backup_to "$target"
      ln -s "$expected_link" "$target"
    else
      # 状态 3: broken symlink → 直接覆盖，无需备份
      ln -sf "$expected_link" "$target"
    fi
    echo "已安装: $name"
    return 0
  fi

  # 状态 4: 普通文件/目录 → 备份后创建
  if [ -e "$target" ]; then
    backup_to "$target"
  fi

  # 状态 5: 不存在 → 直接创建
  ln -s "$expected_link" "$target"
  echo "已安装: $name"
}

# ============================================================
# 特殊配置
# ============================================================

# 特殊配置：zsh
install_zsh() {
  install_config "zsh"
  if [ -e ~/.zshrc ]; then
    # 内容相同则跳过
    if diff -q "$DOTFILES_ROOT/zsh/zshrc" ~/.zshrc >/dev/null 2>&1; then
      echo "~/.zshrc 已是最新"
      return
    fi
    mv ~/.zshrc ~/.zshrc-$TIMESTAMP
  fi
  cp "$DOTFILES_ROOT/zsh/zshrc" ~/.zshrc
  echo "已安装: ~/.zshrc"
}

# 特殊配置：claude（按需 source）
install_claude() {
  # shellcheck source=install-claude.sh
  source "$DOTFILES_ROOT/scripts/install-claude.sh"
  install_claude
}

# 特殊配置：codex（认证依赖 ZHIPU_API_KEY 环境变量）
install_codex() {
  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  警告: ZHIPU_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
  fi
  mkdir -p "$HOME/.codex"
  install_config "codex"
}

# 特殊配置：tmux（依赖 submodule tpm）
install_tmux() {
  git -C "$DOTFILES_ROOT" submodule update --init tmux/3rd/tpm
  install_config "tmux"
}

# 特殊配置：cursor
install_cursor() {
  local target="$HOME/.cursor/mcp.json"
  local template="$DOTFILES_ROOT/cursor/mcp.json"

  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  警告: ZHIPU_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
  fi

  # 备份已存在的文件
  if [ -e "$target" ]; then
    backup_to "$target"
  fi

  # 确保目标目录存在
  mkdir -p "$HOME/.cursor"

  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$template" >"$target"
    echo "已安装: ~/.cursor/mcp.json (已使用 ZHIPU_API_KEY)"
  else
    cp "$template" "$target"
    echo "已安装: ~/.cursor/mcp.json (请手动设置 ZHIPU_API_KEY)"
  fi
}


install_all() {
  for name in $(get_all_config_names); do
    case "$name" in
    zsh)    install_zsh ;;
    claude) install_claude ;;
    codex)  install_codex ;;
    cursor) install_cursor ;;
    tmux)   install_tmux ;;
    *)      install_config "$name" ;;
    esac
  done
}

# ============================================================
# 主函数
# ============================================================

main() {
  local config="$1"

  if [ -z "$config" ]; then
    echo "用法: $0 <配置名|--all>"
    echo ""
    echo "可用配置:"
    for name in $(get_all_config_names); do
      printf "  %-12s %s\n" "$name" "$(get_config_desc "$name")"
    done
    echo ""
    echo "选项:"
    echo "  --all, -a       安装所有配置"
    echo "  --list          仅列出配置名"
    echo "  --list-desc     列出配置名及描述"
    exit 1
  fi

  case "$config" in
  --list)
    for name in $(get_all_config_names); do
      echo "$name"
    done
    ;;
  --list-desc)
    for name in $(get_all_config_names); do
      printf "%s\t%s\n" "$name" "$(get_config_desc "$name")"
    done
    ;;
  --all | -a) install_all ;;
  zsh)    install_zsh ;;
  claude) install_claude ;;
  codex)  install_codex ;;
  cursor) install_cursor ;;
  tmux)   install_tmux ;;
  *)      install_config "$config" ;;
  esac
}

main "$@"
