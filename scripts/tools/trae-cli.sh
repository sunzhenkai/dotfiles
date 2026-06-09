#!/bin/bash
# Trae CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_trae_cli() {
  if ! confirm "是否安装 Trae CLI?" "N"; then
    echo "跳过 Trae CLI 安装"
    return 0
  fi

  echo "正在安装 Trae CLI..."
  sh -c "$(curl -L https://trae.cn/trae-cli/install.sh)"
}
