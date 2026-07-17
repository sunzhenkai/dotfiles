#!/usr/bin/env bash
# Claude Code / Desktop：settings、.claude.json；MCP/skills 由统一 agents sync。
# 由 config.sh source，也可直接执行（会自行设置 DOTFILES_ROOT）。

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
  local settings_template="$DOTFILES_ROOT/claude/settings.json"

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
  local claude_json_source="$DOTFILES_ROOT/claude/.claude.json"

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

  # skills + MCP：统一入口
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

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -e
  DOTFILES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  TIMESTAMP=$(date +%s)
  BACKUP_DIR="$HOME/.config/backups"
  install_claude
fi
