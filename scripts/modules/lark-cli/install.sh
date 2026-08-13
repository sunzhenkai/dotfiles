#!/usr/bin/env bash
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
source "$DOTFILES_ROOT/scripts/tools/common.sh"

if dotf_skip_if_bin lark-cli; then
  exit 0
fi

if ! command -v npx >/dev/null 2>&1; then
  dotf_result_failed "npx 未安装，请先安装 sdk 模块"
  exit 1
fi

echo "正在安装飞书 CLI（npx @larksuite/cli@latest install）..."
if npx -y @larksuite/cli@latest install; then
  if command -v lark-cli >/dev/null 2>&1 || [ -x "${HOME}/.local/bin/lark-cli" ]; then
    dotf_result_changed "lark-cli installed"
  else
    # 安装器可能成功但 bin 尚未进入当前 PATH
    echo "⚠️  安装完成但当前 shell 未找到 lark-cli；新开终端或确认 npm 全局 bin / ~/.local/bin 在 PATH 中"
    dotf_result_changed "lark-cli install finished (PATH may need refresh)"
  fi
else
  dotf_result_failed "lark-cli install failed"
fi
