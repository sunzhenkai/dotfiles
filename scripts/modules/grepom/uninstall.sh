#!/usr/bin/env bash
# 约定式 uninstall — grepom
# 只撤本模块安装到 ~/.local/bin/grepom 的二进制，不猜测 brew/mise。
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

target="${HOME}/.local/bin/grepom"
if [ ! -e "$target" ]; then
  dotf_result_unchanged "grepom binary absent"
  exit 0
fi
if [ -L "$target" ] || [ ! -f "$target" ]; then
  dotf_result_failed "refusing to remove non-regular grepom path"
  exit 1
fi
rm -f "$target"
if [ -e "$target" ]; then
  dotf_result_failed "failed to remove grepom"
  exit 1
fi
dotf_result_changed "removed ~/.local/bin/grepom"
