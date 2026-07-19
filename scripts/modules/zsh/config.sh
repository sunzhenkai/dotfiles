#!/usr/bin/env bash
# zsh：注册表 symlink + ~/.zshrc 复制
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

changed=0
src=$(modules_source zsh)
tgt=$(dotf_expand_path "$(modules_target zsh)")
dotf_ensure_symlink "$src" "$tgt"
[ "${DOTF_CFG_STATUS:-}" = "changed" ] && changed=1

TIMESTAMP=$(date +%s)
zsrc="$DOTFILES_ROOT/config/shell/zsh/zshrc"
ztgt="$HOME/.zshrc"
if [ -e "$ztgt" ]; then
  if ! diff -q "$zsrc" "$ztgt" >/dev/null 2>&1; then
    mv "$ztgt" "$ztgt-$TIMESTAMP"
    cp "$zsrc" "$ztgt"
    changed=1
  fi
else
  cp "$zsrc" "$ztgt"
  changed=1
fi

if [ "$changed" -eq 1 ]; then
  dotf_result_changed "zsh config applied"
else
  dotf_result_unchanged "zsh already configured"
fi
