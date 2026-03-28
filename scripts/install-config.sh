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
  ["claude"]="claude:~/.config/claude"
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

# 特殊配置：claude
install_claude() {
  # 创建 ~/.claude 目录
  local claude_dir="$HOME/.claude"
  if [ ! -d "$claude_dir" ]; then
    mkdir -p "$claude_dir"
  fi

  # 检查环境变量 ZHIPU_API_KEY
  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  Warning: ZHIPU_API_KEY environment variable is not set"
    echo "Please set it in your ~/.envrc or shell config before running the install script"
  fi

  # 安装 settings.json (动态生成以使用环境变量)
  local settings_target="$claude_dir/settings.json"
  local settings_template="$DOTFILES_ROOT/claude/settings.json"

  if [ -e "$settings_target" ]; then
    mv "$settings_target" "$settings_target-$TIMESTAMP"
  fi

  # 使用 sed 替换 API Key
  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$settings_template" >"$settings_target"
    echo "Installed: settings.json (with ZHIPU_API_KEY)"
  else
    cp "$settings_template" "$settings_target"
    echo "Installed: settings.json (please update ANTHROPIC_AUTH_TOKEN manually)"
  fi

  # 安装 .claude.json（仅当仓库中存在模板；否则保留现有 ~/.claude.json 供 Claude Code 状态与 MCP 合并使用）
  local claude_json_target="$HOME/.claude.json"
  local claude_json_source="$DOTFILES_ROOT/claude/.claude.json"

  if [ ! -f "$claude_json_source" ]; then
    echo "⚠️  Skipping ~/.claude.json symlink: no $claude_json_source in dotfiles"
  elif [ -L "$claude_json_target" ]; then
    local current_link
    current_link=$(readlink -f "$claude_json_target" 2>/dev/null || readlink "$claude_json_target")
    local expected_abs
    expected_abs=$(readlink -f "$claude_json_source" 2>/dev/null || echo "$claude_json_source")
    if [ "$current_link" = "$expected_abs" ]; then
      echo "Already installed: .claude.json"
    else
      [ -e "$claude_json_target" ] && mv "$claude_json_target" "$claude_json_target-$TIMESTAMP"
      ln -s "$claude_json_source" "$claude_json_target"
      echo "Installed: .claude.json"
    fi
  else
    [ -e "$claude_json_target" ] && mv "$claude_json_target" "$claude_json_target-$TIMESTAMP"
    ln -s "$claude_json_source" "$claude_json_target"
    echo "Installed: .claude.json"
  fi

  # 安装 .mcp.json (MCP 服务器配置，动态生成以使用环境变量)
  local mcp_target="$claude_dir/.mcp.json"
  local mcp_template="$DOTFILES_ROOT/claude/.mcp.json"

  if [ -e "$mcp_target" ]; then
    mv "$mcp_target" "$mcp_target-$TIMESTAMP"
  fi

  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$mcp_template" >"$mcp_target"
    echo "Installed: .mcp.json (with ZHIPU_API_KEY)"
  else
    cp "$mcp_template" "$mcp_target"
    echo "Installed: .mcp.json (please update Authorization header manually)"
  fi

  # Claude Code 从 ~/.claude.json 顶层 mcpServers 读取 MCP，不会读取 ~/.claude/.mcp.json
  local claude_state="$HOME/.claude.json"
  if [ -L "$claude_state" ] && [ ! -e "$claude_state" ]; then
    echo "⚠️  Warning: ~/.claude.json is a broken symlink; fix it before MCP merge can run"
  else
    python3 - "$mcp_target" "$claude_state" <<'PY'
import json, os, sys, tempfile
from pathlib import Path

mcp_path = Path(sys.argv[1])
dest = Path(os.path.expanduser(sys.argv[2]))
incoming = json.loads(mcp_path.read_text(encoding="utf-8"))["mcpServers"]
if dest.exists():
    data = json.loads(dest.read_text(encoding="utf-8"))
else:
    data = {}
data.setdefault("mcpServers", {})
data["mcpServers"].update(incoming)
text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
dest.parent.mkdir(parents=True, exist_ok=True)
fd, tmp = tempfile.mkstemp(
    dir=str(dest.parent), prefix=".claude.json.", suffix=".tmp", text=True
)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, dest)
except Exception:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise
PY
    echo "Merged MCP servers into ~/.claude.json (Claude Code user scope)"
  fi

  if [ -n "${SUDO_USER:-}" ] && [ "$(id -u)" -eq 0 ]; then
    chown -R "$SUDO_USER:" "$claude_dir" 2>/dev/null || true
    chown "$SUDO_USER:" "$claude_state" 2>/dev/null || true
    echo "Adjusted ownership for \$SUDO_USER on ~/.claude and ~/.claude.json"
  fi
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
    claude) install_claude ;;
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
  claude) install_claude ;;
  git) install_git ;;
  git-global) install_git_global ;;
  *) install_config "$config" ;;
  esac
}

main "$@"
