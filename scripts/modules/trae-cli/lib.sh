#!/bin/bash
# Trae CLI 安装

source "$SCRIPT_DIR/scripts/lib/common.sh"

install_trae_cli() {
  echo "正在安装 Trae CLI..."
  dotf_fetch_run --interp sh https://trae.cn/trae-cli/install.sh
}
