#!/bin/bash
# D2 安装

source "$SCRIPT_DIR/scripts/lib/common.sh"

install_d2() {
  echo "正在安装 D2..."
  dotf_fetch_run --interp sh https://d2lang.com/install.sh --
}
