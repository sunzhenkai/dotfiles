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
  opencode)  echo "agents/vendors/opencode:~/.config/opencode" ;;
  claude)    echo "agents/vendors/claude:~/.config/claude" ;;
  codex)     echo "agents/vendors/codex/config.toml:~/.codex/config.toml" ;;
  cursor)    echo "agents/vendors/cursor/mcp.json:~/.cursor/mcp.json" ;;
  kimi-code) echo "agents/vendors/kimi-code/config.toml:~/.kimi-code/config.toml" ;;
  agents)    echo "agents:~/.local/share/dotfiles-agents" ;;
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
  codex)     echo "Codex CLI 配置（MiniMax，无需登录）" ;;
  cursor)    echo "Cursor 编辑器 MCP 配置" ;;
  kimi-code) echo "Kimi Code CLI 配置（首次安装；已有则跳过以免覆盖登录凭证）" ;;
  agents)    echo "同步 agents：skills/commands + MCP/profiles（可用 --doctor）" ;;
  logseq)    echo "Logseq 笔记配置" ;;
  iterm2)    echo "iTerm2 终端模拟器配置" ;;
  *)         echo "$1" ;;
  esac
}

# 获取所有配置名（排序后，空格分隔）
get_all_config_names() {
  echo "agents alacritty claude codex cursor fcitx5 ghostty git helix hypr iterm2 k9s kimi-code kitty logseq nvim opencode shell_gpt starship tmux wezterm yazi zed zellij zsh"
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

# 创建 symlink（带备份），source 为仓库内相对路径，target 为绝对路径。
# 与 install_config 同样的 symlink+backup 策略，供需要安装到子目录的额外文件复用。
link_file() {
  local source="$1"
  local target="$2"
  local expected_link="$DOTFILES_ROOT/$source"
  local expected_abs
  expected_abs=$(readlink -f "$expected_link" 2>/dev/null || echo "$expected_link")

  # 已是正确 symlink → 跳过
  if [ -L "$target" ]; then
    local current_link
    current_link=$(readlink -f "$target" 2>/dev/null || readlink "$target")
    if [ "$current_link" = "$expected_abs" ]; then
      return 0
    fi
    ln -sf "$expected_link" "$target"
    return 0
  fi
  # 普通文件/目录存在 → 备份后创建
  if [ -e "$target" ]; then
    backup_to "$target"
  fi
  ln -s "$expected_link" "$target"
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

# 统一 agents sync（skills + MCP/env；可传 --skills-only/--env-only/--profile/--doctor）
sync_agents() {
  "$DOTFILES_ROOT/scripts/agents/sync.sh" "$@"
}

install_agents() {
  # 其余参数透传（如 --doctor --profile research）
  sync_agents all "$@"
}

# 特殊配置：claude（settings / .claude.json；MCP/skills 走统一 agents sync）
install_claude() {
  local claude_dir="$HOME/.claude"
  if [ ! -d "$claude_dir" ]; then
    mkdir -p "$claude_dir"
  fi

  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  警告: ZHIPU_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
  fi

  local settings_target="$claude_dir/settings.json"
  local settings_template="$DOTFILES_ROOT/agents/vendors/claude/settings.json"

  if [ -e "$settings_target" ]; then
    mv "$settings_target" "$settings_target-$TIMESTAMP"
  fi

  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$settings_template" >"$settings_target"
    echo "已安装: settings.json (已使用 ZHIPU_API_KEY)"
  else
    cp "$settings_template" "$settings_target"
    echo "已安装: settings.json (请手动设置 ZHIPU_API_KEY)"
  fi

  local claude_json_target="$HOME/.claude.json"
  local claude_json_source="$DOTFILES_ROOT/agents/vendors/claude/.claude.json"

  if [ ! -f "$claude_json_source" ]; then
    echo "⚠️  跳过 ~/.claude.json symlink: dotfiles 中不存在 $claude_json_source"
  elif [ -L "$claude_json_target" ]; then
    local current_link
    current_link=$(readlink -f "$claude_json_target" 2>/dev/null || readlink "$claude_json_target")
    local expected_abs
    expected_abs=$(readlink -f "$claude_json_source" 2>/dev/null || echo "$claude_json_source")
    if [ "$current_link" = "$expected_abs" ]; then
      echo "已安装: .claude.json"
    else
      if [ -e "$claude_json_target" ]; then
        mkdir -p "$BACKUP_DIR"
        mv "$claude_json_target" "$BACKUP_DIR/.claude.json-${TIMESTAMP}"
        echo "已备份 .claude.json 到 $BACKUP_DIR/.claude.json-${TIMESTAMP}"
      fi
      ln -sf "$claude_json_source" "$claude_json_target"
      echo "已安装: .claude.json"
    fi
  else
    if [ -e "$claude_json_target" ]; then
      mkdir -p "$BACKUP_DIR"
      mv "$claude_json_target" "$BACKUP_DIR/.claude.json-${TIMESTAMP}"
      echo "已备份 .claude.json 到 $BACKUP_DIR/.claude.json-${TIMESTAMP}"
    fi
    ln -s "$claude_json_source" "$claude_json_target"
    echo "已安装: .claude.json"
  fi

  if [ -x "$DOTFILES_ROOT/scripts/agents/sync.sh" ]; then
    "$DOTFILES_ROOT/scripts/agents/sync.sh" claude
  else
    echo "⚠️  跳过 agents sync：找不到 scripts/agents/sync.sh"
  fi

  if [ -n "${SUDO_USER:-}" ] && [ "$(id -u)" -eq 0 ]; then
    local claude_state="$HOME/.claude.json"
    chown -R "$SUDO_USER:" "$claude_dir" 2>/dev/null || true
    chown "$SUDO_USER:" "$claude_state" 2>/dev/null || true
    echo "已为 \$SUDO_USER 调整 ~/.claude 和 ~/.claude.json 的所有者"
  fi
}

# 特殊配置：codex（依赖 MINIMAX_API_KEY 环境变量，无需 OpenAI 登录）
#
# ~/.codex/config.toml 不再使用软链，而是由「仓库 base + 本地 local」合并生成
# 的真实文件。原因：codex 会把 [projects."<path>"] 自动写进该文件，软链会穿透
# 污染仓库。projects 维护在 agents/vendors/codex/config.local.toml（gitignore），安装时合并。
#
# 注意：每次安装都用 base + local 重新覆盖 ~/.codex/config.toml。codex 新增的
#       信任不会自动回抽——需手动把对应 [projects."<path>"] 块加入 local 后重跑。
install_codex() {
  if [ -z "$MINIMAX_API_KEY" ]; then
    echo "⚠️  警告: MINIMAX_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
    echo "（本配置使用自定义 provider，无需 codex login / OPENAI_API_KEY）"
  fi

  mkdir -p "$HOME/.codex"

  local base="$DOTFILES_ROOT/agents/vendors/codex/config.toml"
  local local_cfg="$DOTFILES_ROOT/agents/vendors/codex/config.local.toml"
  local target="$HOME/.codex/config.toml"

  # 旧机制遗留：target 若是软链则移除，改用合并生成
  [ -L "$target" ] && rm "$target" && echo "已移除旧的 config.toml 软链"

  # 合并 base + local → target（真实文件，非软链；每次覆盖生成）
  {
    cat "$base"
    if [ -f "$local_cfg" ]; then
      echo ""
      echo "# ============================================================"
      echo "# ↓↓↓ 以下来自 agents/vendors/codex/config.local.toml（机器特定，不纳入 git） ↓↓↓"
      cat "$local_cfg"
    fi
  } > "$target"
  echo "已安装: ~/.codex/config.toml（base + local 合并生成）"

  # 模型能力目录（model catalog，只读，仍用软链）
  mkdir -p "$HOME/.codex/model-catalogs"
  link_file "agents/vendors/codex/model-catalogs/custom-catalog.json" "$HOME/.codex/model-catalogs/custom-catalog.json"
  echo "已安装: ~/.codex/model-catalogs/custom-catalog.json"

  sync_agents codex
}

# 特殊配置：tmux（依赖 submodule tpm；补装 tmux-yank 剪贴板工具）
install_tmux() {
  git -C "$DOTFILES_ROOT" submodule update --init tmux/3rd/tpm
  install_config "tmux"

  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/tools/common.sh"
  install_tmux_clipboard_deps || true
}

# 特殊配置：cursor（MCP + skills 由统一 agents sync）
install_cursor() {
  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  警告: ZHIPU_API_KEY 环境变量未设置"
    echo "请在 ~/.envrc 或 shell 配置中设置后再运行安装脚本"
  fi

  mkdir -p "$HOME/.cursor"
  sync_agents cursor
}


install_opencode() {
  install_config "opencode"
  # skills + MCP 一并同步；MCP 写入 agents/vendors/opencode/opencode.json
  sync_agents opencode
}

# 特殊配置：kimi-code
# ~/.kimi-code/config.toml 用复制而非软链：/login 会写入 oauth/凭证相关字段，
# 软链会穿透污染仓库；已存在的配置也不覆盖，避免抹掉登录状态。
install_kimi_code_config() {
  local source="$DOTFILES_ROOT/agents/vendors/kimi-code/config.toml"
  local target="$HOME/.kimi-code/config.toml"

  mkdir -p "$HOME/.kimi-code"

  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "已存在: ~/.kimi-code/config.toml（跳过覆盖，避免丢失 /login 凭证）"
    echo "如需重置，请先备份并删除该文件后重新运行: dotf -c kimi-code"
  else
    cp "$source" "$target"
    echo "已安装: ~/.kimi-code/config.toml"
    echo "提示: 启动 kimi 后执行 /login 完成鉴权"
  fi

  # skills + MCP 走统一 agents sync（commands 对 kimi 为 skip）
  sync_agents kimi-code
}

install_all() {
  for name in $(get_all_config_names); do
    case "$name" in
    agents)   ;; # 各工具安装时已 sync；全量末尾再统一跑一次
    zsh)      install_zsh ;;
    claude)   install_claude ;;
    codex)    install_codex ;;
    cursor)   install_cursor ;;
    opencode) install_opencode ;;
    kimi-code) install_kimi_code_config ;;
    tmux)     install_tmux ;;
    *)        install_config "$name" ;;
    esac
  done
  sync_agents all
}

# ============================================================
# 主函数
# ============================================================

main() {
  local config="${1:-}"

  if [ -z "$config" ]; then
    echo "用法: $0 <配置名|--all> [agents 选项...]"
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
    echo ""
    echo "agents 附加选项（仅 agents）:"
    echo "  --doctor --profile NAME --skills-only --env-only --dry-run --strict"
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
  agents)
    shift
    install_agents "$@"
    ;;
  zsh)      install_zsh ;;
  claude)   install_claude ;;
  codex)    install_codex ;;
  cursor)   install_cursor ;;
  opencode) install_opencode ;;
  kimi-code) install_kimi_code_config ;;
  tmux)     install_tmux ;;
  *)        install_config "$config" ;;
  esac
}

main "$@"
