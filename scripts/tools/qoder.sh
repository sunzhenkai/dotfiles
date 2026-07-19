#!/bin/bash
# Qoder CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_qoder() {
  echo "正在安装 Qoder CLI..."
  curl -fsSL https://qoder.com.cn/install | bash
  # curl -fsSL https://qoder.com/install | bash
}
