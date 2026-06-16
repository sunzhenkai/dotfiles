#!/bin/bash
# Kimi Code CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_kimi_code() {
  if ! confirm "是否安装 Kimi Code CLI?" "N"; then
    echo "跳过 Kimi Code CLI 安装"
    return 0
  fi

  echo "正在安装 Kimi Code CLI..."
  curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
}
