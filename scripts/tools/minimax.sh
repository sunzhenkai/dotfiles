#!/bin/bash
# MiniMax CLI 安装
# 配置目录: ~/.mmx（config.json 含 OAuth/API key 凭证，dotfiles 不管理）
# CLI 包: mmx-cli（bin: mmx）
# 文档: https://github.com/MiniMax-AI/cli

source "$SCRIPT_DIR/scripts/tools/common.sh"

# npm 全局 bin（mise / ~/.local）临时加入 PATH
_ensure_minimax_path() {
  local d prefix
  prefix="$(npm prefix -g 2>/dev/null || true)"
  for d in "${prefix:+$prefix/bin}" "$HOME/.local/bin"; do
    if [[ -n "$d" && -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_minimax() {
  _ensure_minimax_path

  if command -v mmx &>/dev/null; then
    echo "MiniMax CLI 已安装: $(command -v mmx) ($(mmx --version 2>/dev/null || echo '?'))"
    return 0
  fi

  if ! command -v npm &>/dev/null; then
    echo "✗ 需要 Node.js/npm 才能安装 MiniMax CLI；请先: dotf sdk -i"
    return 1
  fi

  echo "正在安装 MiniMax CLI（npm: mmx-cli）..."
  if ! npm install -g mmx-cli@latest; then
    echo "✗ mmx-cli 安装失败"
    return 1
  fi

  _ensure_minimax_path

  if command -v mmx &>/dev/null; then
    echo "✓ MiniMax CLI 已就绪: $(command -v mmx)"
    return 0
  fi

  echo "⚠️  安装完成但未找到 mmx，请确认 npm 全局 bin 已在 PATH 中后重新打开终端"
  echo "  提示: npm prefix -g → 将其 /bin 加入 PATH"
  return 1
}
