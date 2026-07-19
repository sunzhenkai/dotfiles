#!/bin/bash
# D2 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_d2() {
  echo "正在安装 D2..."
  curl -fsSL https://d2lang.com/install.sh | sh -s --
}
