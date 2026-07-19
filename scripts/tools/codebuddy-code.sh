#!/bin/bash
# CodeBuddy Code CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_codebuddy_code() {
  echo "正在安装 CodeBuddy Code CLI..."
  npm install -g @tencent-ai/codebuddy-code
}
