#!/bin/bash
# Codex CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_codex() {
  if ! confirm "是否安装 Codex CLI?" "N"; then
    echo "跳过 Codex CLI 安装"
    return 0
  fi

  echo "正在安装 Codex CLI..."
  npm install -g @openai/codex
}
