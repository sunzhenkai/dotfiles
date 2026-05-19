#!/bin/bash
# Cursor CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_cursor_cli() {
  if ! confirm "是否安装 Cursor CLI?"; then
    echo "跳过 Cursor CLI 安装"
    return 0
  fi

  echo "正在安装 Cursor CLI..."
  curl https://cursor.com/install -fsS | bash
}
