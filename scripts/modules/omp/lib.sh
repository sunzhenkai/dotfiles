#!/bin/bash
# oh-my-pi (omp) coding agent CLI 安装
# 上游: https://github.com/can1357/oh-my-pi
# 官方安装脚本: https://omp.sh/install（默认优先 bun 全局包，无 bun 或架构
# 不匹配时回退 GitHub Releases 预编译二进制；统一落位 ~/.local/bin/omp）

source "$SCRIPT_DIR/scripts/lib/common.sh"

# 官方安装器落位 ~/.local/bin，临时确保在 PATH（新终端由 paths.zsh 加载）
_ensure_omp_path() {
  local d
  for d in "$HOME/.local/bin"; do
    if [[ -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_omp() {
  _ensure_omp_path

  echo "正在安装 oh-my-pi (omp) coding agent..."
  # 强制官方源：镜像可能未收录 @oh-my-pi 包（与 pi 模块同理）
  curl -fsSL https://omp.sh/install | npm_config_registry=https://registry.npmjs.org sh

  _ensure_omp_path

  if command -v omp &>/dev/null || [[ -x "$HOME/.local/bin/omp" ]]; then
    echo "✓ omp 已就绪: $(command -v omp 2>/dev/null || echo "$HOME/.local/bin/omp") ($(omp --version 2>/dev/null || echo '?'))"
    return 0
  fi
  echo "⚠️  安装完成但未找到 omp，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
  return 1
}
