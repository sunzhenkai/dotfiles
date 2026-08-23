#!/usr/bin/env bash
# Logseq：~/.logseq 必须是真实目录。
# 禁止把整个 ~/.logseq 软链进仓库——graphs/plugins 是笔记缓存，会写入密钥。
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

src_rel="config/tools/logseq"
src="${DOTFILES_ROOT}/${src_rel}"
tgt=$(dotf_expand_path "$(modules_target logseq)")
changed=0

if [ -L "$tgt" ]; then
  echo "拆除整目录软链: ~/.logseq → $(readlink "$tgt")"
  changed=1
fi
dotf_ensure_real_dir "$tgt"
mkdir -p "$tgt/config"

for item in graphs plugins graphs.edn; do
  if [ -e "$src/$item" ] || [ -L "$src/$item" ]; then
    echo "迁出运行时: $item → ~/.logseq/$item"
    dotf_migrate_runtime "$src/$item" "$tgt/$item"
    changed=1
  fi
done

# 只链声明式配置；settings 为插件偏好（勿写入 token）
dotf_ensure_symlink "${src_rel}/config/config.edn" "$tgt/config/config.edn"
[ "${DOTF_CFG_STATUS:-}" = "changed" ] && changed=1
dotf_ensure_symlink "${src_rel}/config/plugins.edn" "$tgt/config/plugins.edn"
[ "${DOTF_CFG_STATUS:-}" = "changed" ] && changed=1
dotf_ensure_symlink "${src_rel}/preferences.json" "$tgt/preferences.json"
[ "${DOTF_CFG_STATUS:-}" = "changed" ] && changed=1
dotf_ensure_symlink "${src_rel}/settings" "$tgt/settings"
[ "${DOTF_CFG_STATUS:-}" = "changed" ] && changed=1

if [ "$changed" -eq 1 ]; then
  dotf_result_changed "logseq: ~/.logseq is a real dir; config files linked"
else
  dotf_result_unchanged "logseq already configured"
fi
