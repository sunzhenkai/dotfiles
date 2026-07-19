#!/usr/bin/env bash
# 通用注册表 symlink 配置
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init
dotf_registry_symlink_config
