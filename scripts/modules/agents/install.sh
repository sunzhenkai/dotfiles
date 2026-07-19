#!/usr/bin/env bash
# agents 聚合安装：实际 CLI 安装由 depends_on 展开的单工具动作完成。
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/handler_common.sh"
dotf_handler_init

echo "agents: 聚合安装入口（单工具由计划中的独立 install 动作执行）"
echo "配置同步请运行: dotf agents -c"
dotf_result_unchanged "agents install delegated to tool modules via depends_on"
