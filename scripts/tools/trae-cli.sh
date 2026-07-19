#!/bin/bash
# Trae CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_trae_cli() {
  echo "正在安装 Trae CLI..."
  sh -c "$(curl -L https://trae.cn/trae-cli/install.sh)"
}
