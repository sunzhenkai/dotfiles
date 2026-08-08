#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"

if ! command -v npm >/dev/null 2>&1; then
  dotf_result_failed "npm 未安装，请先安装 sdk 模块"
  exit 1
fi

if npm install -g dingtalk-workspace-cli --registry=https://registry.npmmirror.com; then
  dotf_result_changed "dws installed"
else
  dotf_result_failed "dws install failed"
fi
