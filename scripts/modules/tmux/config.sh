#!/usr/bin/env bash
# tmux：submodule + symlink + 剪贴板依赖
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/tools/common.sh"

git -C "$DOTFILES_ROOT" submodule update --init config/multiplexers/tmux/3rd/tpm
src=$(modules_source tmux)
tgt=$(dotf_expand_path "$(modules_target tmux)")
dotf_ensure_symlink "$src" "$tgt"
status="${DOTF_CFG_STATUS:-changed}"
install_tmux_clipboard_deps || true
if [ "$status" = "unchanged" ]; then
  dotf_result_unchanged "tmux already linked"
else
  dotf_result_changed "tmux configured"
fi
