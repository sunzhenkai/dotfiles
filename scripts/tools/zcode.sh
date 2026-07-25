#!/bin/bash
# ZCode CLI 安装
# 桌面端数据目录: ~/.zcode/{cli,server,v2}
# CLI 包: zcode-app-cli（bin: zcode）
# 文档: https://zcode.z.ai/en/docs/install

source "$SCRIPT_DIR/scripts/tools/common.sh"

# npm 全局 bin（mise / ~/.local）临时加入 PATH
_ensure_zcode_path() {
  local d prefix
  prefix="$(npm prefix -g 2>/dev/null || true)"
  for d in "${prefix:+$prefix/bin}" "$HOME/.local/bin"; do
    if [[ -n "$d" && -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_zcode() {
  _ensure_zcode_path

  if command -v zcode &>/dev/null; then
    echo "ZCode CLI 已安装: $(command -v zcode) ($(zcode --version 2>/dev/null || echo '?'))"
    return 0
  fi

  if ! command -v npm &>/dev/null; then
    echo "✗ 需要 Node.js/npm 才能安装 ZCode CLI；请先: dotf sdk -i"
    echo "  桌面端也可从 https://zcode.z.ai 下载（数据目录仍为 ~/.zcode）"
    return 1
  fi

  echo "正在安装 ZCode CLI（npm: zcode-app-cli）..."
  if ! npm install -g zcode-app-cli@latest; then
    echo "✗ zcode-app-cli 安装失败"
    return 1
  fi

  _ensure_zcode_path

  if command -v zcode &>/dev/null; then
    echo "✓ ZCode CLI 已就绪: $(command -v zcode)"
    return 0
  fi

  echo "⚠️  安装完成但未找到 zcode，请确认 npm 全局 bin 已在 PATH 中后重新打开终端"
  echo "  提示: npm prefix -g → 将其 /bin 加入 PATH"
  return 1
}
