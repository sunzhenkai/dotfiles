#!/bin/bash
# Qoder CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_qoder() {
  if ! confirm "是否安装 Qoder CLI?" "N"; then
    echo "跳过 Qoder CLI 安装"
    return 0
  fi

  echo "正在安装 Qoder CLI..."
  curl -fsSL https://qoder.com.cn/install | bash
  # curl -fsSL https://qoder.com/install | bash
}
