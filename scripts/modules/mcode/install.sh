#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/lib/common.sh"

if dotf_skip_if_bin mcode; then
  exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
  dotf_result_failed "npm 未安装，请先安装 sdk 模块"
  exit 1
fi

echo "正在安装 MiniMax Code CLI（npm install -g @minimax-ai/code）..."
if npm install -g @minimax-ai/code@latest; then
  if command -v mcode >/dev/null 2>&1 || [ -x "${HOME}/.local/bin/mcode" ]; then
    dotf_result_changed "mcode installed"
  else
    # 安装器可能成功但 bin 尚未进入当前 PATH
    echo "⚠️  安装完成但当前 shell 未找到 mcode；新开终端或确认 npm 全局 bin 在 PATH 中"
    dotf_result_changed "mcode install finished (PATH may need refresh)"
  fi
else
  dotf_result_failed "mcode install failed"
fi
