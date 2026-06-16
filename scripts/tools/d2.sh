#!/bin/bash
# D2 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_d2() {
  if ! confirm "是否安装 D2?" "N"; then
    echo "跳过 D2 安装"
    return 0
  fi

  echo "正在安装 D2..."
  curl -fsSL https://d2lang.com/install.sh | sh -s --
}
