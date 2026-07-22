#!/bin/bash
# Pi coding agent CLI 安装
# 官方文档: https://pi.dev/docs/latest/
# 包: @earendil-works/pi-coding-agent

source "$SCRIPT_DIR/scripts/tools/common.sh"

# 常见 npm 全局 bin（mise / ~/.local）临时加入 PATH
_ensure_pi_path() {
  local d prefix
  prefix="$(npm prefix -g 2>/dev/null || true)"
  for d in "${prefix:+$prefix/bin}" "$HOME/.local/bin"; do
    if [[ -n "$d" && -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_pi() {
  _ensure_pi_path

  if command -v pi &>/dev/null; then
    echo "Pi 已安装: $(command -v pi) ($(pi --version 2>/dev/null || echo '?'))"
    return 0
  fi

  if ! command -v npm &>/dev/null; then
    echo "✗ 需要 Node.js/npm（Node ≥ 22.19）才能安装 Pi；请先: dotf sdk -i"
    return 1
  fi

  echo "正在安装 Pi coding agent（官方 install.sh）..."
  # 无 TTY 时官方脚本会自动确认 install，不阻塞 CI/非交互
  curl -fsSL https://pi.dev/install.sh | sh

  _ensure_pi_path

  if command -v pi &>/dev/null; then
    echo "✓ Pi 已就绪: $(command -v pi)"
  else
    echo "⚠️  安装完成但未找到 pi，请确认 npm 全局 bin 已在 PATH 中后重新打开终端"
    echo "  提示: npm prefix -g → 将其 /bin 加入 PATH"
    return 1
  fi
}
