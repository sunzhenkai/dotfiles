#!/usr/bin/env bash
# DeepSeek Harness CLI（dsh）安装：npm -g @deepseek-ai/dsh
# 依赖：sdk（Node/npm）。profile 插件管理（dsh plugin）还需 pnpm（mise/corepack）。

source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"

if dotf_skip_if_bin dsh; then
  exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
  dotf_result_failed "npm 未安装，请先安装 sdk 模块"
  exit 1
fi

echo "正在安装 DeepSeek Harness CLI（npm install -g @deepseek-ai/dsh）..."
if npm install -g @deepseek-ai/dsh@latest; then
  if command -v dsh >/dev/null 2>&1 || [ -x "${HOME}/.local/bin/dsh" ]; then
    dotf_result_changed "dsh installed"
  else
    echo "⚠️  安装完成但当前 shell 未找到 dsh；新开终端或确认 npm 全局 bin / ~/.local/bin 在 PATH 中"
    dotf_result_changed "dsh install finished (PATH may need refresh)"
  fi
else
  dotf_result_failed "dsh install failed"
fi
