#!/usr/bin/env bash
# Herdr：只链接配置文件，避免 server/session/socket/runtime 污染仓库
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

src=$(modules_source herdr)
tgt=$(dotf_expand_path "$(modules_target herdr)")

# Herdr writes runtime state next to config.toml; keep that directory real.
dotf_ensure_real_dir "$tgt"
dotf_ensure_symlink "$src/config.toml" "$tgt/config.toml"
status="${DOTF_CFG_STATUS:-changed}"
if [ "$status" = "unchanged" ]; then
  dotf_result_unchanged "herdr config already linked"
else
  dotf_result_changed "herdr config applied"
fi
