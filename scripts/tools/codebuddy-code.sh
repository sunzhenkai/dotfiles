#!/bin/bash
# CodeBuddy Code CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_codebuddy_code() {
  if ! confirm "是否安装 CodeBuddy Code CLI?" "N"; then
    echo "跳过 CodeBuddy Code CLI 安装"
    return 0
  fi

  echo "正在安装 CodeBuddy Code CLI..."
  npm install -g @tencent-ai/codebuddy-code
}
