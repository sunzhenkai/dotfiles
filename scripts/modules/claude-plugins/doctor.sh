#!/usr/bin/env bash
# claude-plugins L1：desired set 在位检查（只读；由 `dotf claude-plugins -d --deep` 触发）
# 行协议: pass|fail <scope>: <message>（见 scripts/lib/doctor_l0.sh 的 map_status）
# 注意：本文件由 doctor_run.sh source 执行，禁止使用 exit。
: "${DOTFILES_ROOT:=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
source "$DOTFILES_ROOT/scripts/modules/claude-plugins/lib.sh"

claude_plugins_doctor() {
  local cli repo spec failed=0

  if ! cli="$(claude_plugins_cli)"; then
    echo "fail  cli: 未找到 claude CLI"
    echo "      建议: dotf claude-code -i"
    return 1
  fi
  echo "pass  cli: $cli"

  # shellcheck disable=SC2046 # desired set 条目无空格，词分割即逐条遍历
  for repo in $(claude_plugins_marketplaces); do
    if claude_plugins_marketplace_known "$cli" "$repo"; then
      echo "pass  marketplace: $repo"
    else
      echo "fail  marketplace: 未配置 $repo"
      echo "      建议: dotf claude-plugins -i"
      failed=1
    fi
  done

  # shellcheck disable=SC2046 # 同上
  for spec in $(claude_plugins_plugins); do
    if claude_plugins_plugin_installed "$cli" "$spec"; then
      echo "pass  plugin: $spec"
    else
      echo "fail  plugin: 未安装 $spec"
      echo "      建议: dotf claude-plugins -i"
      failed=1
    fi
  done

  return "$failed"
}

claude_plugins_doctor
