#!/bin/bash
# claude-plugins：Claude Code 插件 desired set 同步（marketplace + 插件）
#
# 复用方式：新增 marketplace / 插件只需改下面两个列表，然后：
#   dotf claude-plugins -i    # 幂等同步（已在位则 unchanged）
#   dotf claude-plugins -d    # L0 诊断
#   DOTF_DEEP=1 dotf claude-plugins -d   # 追加 L1：desired set 在位检查（--deep 仅 agents 直连）
# `dotf agents -i` 会经 AGENTS_INSTALL_BUNDLE 展开到本模块。
#
# 前置：claude CLI 由 claude-code 模块负责安装（本模块 depends_on: claude-code）。
# 插件的实际使用还需本机 Codex 登录（`codex login`）——凭据属本机自管，不入仓库。

# 期望配置的 marketplace 源（`claude plugin marketplace add` 的实参，<owner/repo>）
claude_plugins_marketplaces() {
  printf '%s\n' "openai/codex-plugin-cc"
}

# 期望安装的插件（`claude plugin install` 的实参，<plugin>@<marketplace>）
claude_plugins_plugins() {
  printf '%s\n' "codex@openai-codex"
}

# 解析 claude CLI 真实路径：PATH 优先，回退 ~/.local/bin（官方布局）
# 用法: claude_plugins_cli → stdout 打印路径；找不到返回 1
claude_plugins_cli() {
  local resolved local_path
  resolved="$(command -v claude 2>/dev/null || true)"
  if [ -n "$resolved" ] && [ -e "$resolved" ]; then
    printf '%s\n' "$resolved"
    return 0
  fi
  local_path="$HOME/.local/bin/claude"
  if [ -e "$local_path" ] && [ -x "$local_path" ]; then
    printf '%s\n' "$local_path"
    return 0
  fi
  return 1
}

# marketplace 是否已配置：按源 repo 匹配 "Source: GitHub (<repo>)" 行
claude_plugins_marketplace_known() {
  local cli="$1" repo="$2"
  "$cli" plugin marketplace list 2>/dev/null | grep -Fq "($repo)"
}

# 插件是否已安装：匹配 "❯ <spec>" 行（词边界匹配，避免前缀误判）
claude_plugins_plugin_installed() {
  local cli="$1" spec="$2" pat
  pat="${spec//./\\.}"
  "$cli" plugin list 2>/dev/null | grep -Eq "(^|[[:space:]])${pat}([[:space:]]|\$)"
}

# 幂等同步 desired set；成功返回 0。
# 副作用：CLAUDE_PLUGINS_SYNC_CHANGED=1 表示本次发生了安装动作（供结果协议区分 changed/unchanged）
claude_plugins_sync() {
  local cli repo spec rc=0
  CLAUDE_PLUGINS_SYNC_CHANGED=0

  if ! cli="$(claude_plugins_cli)"; then
    echo "✗ 未找到 claude CLI" >&2
    echo "  先安装 Claude Code: dotf claude-code -i" >&2
    return 1
  fi

  # shellcheck disable=SC2046 # desired set 条目无空格，词分割即逐条遍历
  for repo in $(claude_plugins_marketplaces); do
    if claude_plugins_marketplace_known "$cli" "$repo"; then
      echo "  = marketplace 已配置: $repo"
      continue
    fi
    echo "  + 添加 marketplace: $repo"
    if ! "$cli" plugin marketplace add "$repo"; then
      echo "✗ marketplace add 失败: $repo" >&2
      rc=1
      continue
    fi
    CLAUDE_PLUGINS_SYNC_CHANGED=1
  done

  # shellcheck disable=SC2046 # 同上
  for spec in $(claude_plugins_plugins); do
    if claude_plugins_plugin_installed "$cli" "$spec"; then
      echo "  = 插件已安装: $spec"
      continue
    fi
    echo "  + 安装插件: $spec"
    if ! "$cli" plugin install "$spec"; then
      echo "✗ plugin install 失败: $spec" >&2
      rc=1
      continue
    fi
    # shellcheck disable=SC2034 # 跨脚本产出：install.sh 读取该标志区分 changed/unchanged
    CLAUDE_PLUGINS_SYNC_CHANGED=1
  done

  return "$rc"
}
