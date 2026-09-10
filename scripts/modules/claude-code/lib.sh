#!/bin/bash
# Claude Code CLI 安装
# 官方文档: https://docs.anthropic.com/en/docs/claude-code/setup
# 原生安装器默认装到 ~/.local/bin/claude（用户级，无需 sudo / npm）

source "$SCRIPT_DIR/scripts/lib/common.sh"

_ensure_claude_path() {
  local d
  for d in "$HOME/.local/bin"; do
    if [[ -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_claude_code() {
  _ensure_claude_path

  if command -v claude &>/dev/null; then
    echo "Claude Code CLI 已安装: $(command -v claude) ($(claude --version 2>/dev/null || echo '?'))"
    return 0
  fi

  echo "正在安装 Claude Code CLI（官方原生安装器）..."
  if ! curl -fsSL https://claude.ai/install.sh | bash; then
    echo "✗ Claude Code CLI 安装失败"
    echo "  备选: npm install -g @anthropic-ai/claude-code（需先 dotf sdk -i）"
    return 1
  fi

  _ensure_claude_path

  if command -v claude &>/dev/null || [[ -x "$HOME/.local/bin/claude" ]]; then
    echo "✓ Claude Code CLI 已就绪: $(command -v claude 2>/dev/null || echo "$HOME/.local/bin/claude")"
    return 0
  fi

  echo "⚠️  安装完成但未找到 claude，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
  echo "  提示: zsh/modules/paths.zsh 已加载 ~/.local/bin"
  return 1
}
