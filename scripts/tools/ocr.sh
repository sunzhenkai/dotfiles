#!/bin/bash
# Open Code Review (OCR) CLI 安装
# 包: @alibaba-group/open-code-review（bin: ocr）
# 文档: https://github.com/alibaba/open-code-review

source "$SCRIPT_DIR/scripts/tools/common.sh"

# npm 全局 bin（mise / ~/.local）临时加入 PATH
_ensure_ocr_path() {
  local d prefix
  prefix="$(npm prefix -g 2>/dev/null || true)"
  for d in "${prefix:+$prefix/bin}" "$HOME/.local/bin"; do
    if [[ -n "$d" && -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

install_ocr() {
  _ensure_ocr_path

  if command -v ocr &>/dev/null; then
    echo "Open Code Review 已安装: $(command -v ocr) ($(ocr --version 2>/dev/null || echo '?'))"
    return 0
  fi

  if ! command -v npm &>/dev/null; then
    echo "✗ 需要 Node.js/npm 才能安装 Open Code Review；请先: dotf sdk -i"
    return 1
  fi

  echo "正在安装 Open Code Review（npm: @alibaba-group/open-code-review）..."
  if ! npm install -g @alibaba-group/open-code-review@latest; then
    echo "✗ @alibaba-group/open-code-review 安装失败"
    return 1
  fi

  _ensure_ocr_path

  if command -v ocr &>/dev/null; then
    echo "✓ Open Code Review 已就绪: $(command -v ocr)"
    return 0
  fi

  echo "⚠️  安装完成但未找到 ocr，请确认 npm 全局 bin 已在 PATH 中后重新打开终端"
  echo "  提示: npm prefix -g → 将其 /bin 加入 PATH"
  return 1
}
