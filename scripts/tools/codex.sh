#!/bin/bash
# Codex CLI 安装

source "$SCRIPT_DIR/scripts/tools/common.sh"

install_codex() {
  echo "正在安装 Codex CLI..."
  npm install -g @openai/codex
}
