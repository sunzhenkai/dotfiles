#!/bin/bash
# Pi coding agent CLI 安装
# 官方文档: https://pi.dev/docs/latest/
# 包: @earendil-works/pi-coding-agent

source "$SCRIPT_DIR/scripts/lib/common.sh"

# 默认扩展包（目标管理 + 子代理委派 + powerline footer + 上下文压缩
# + 可观测性 + todo + 代码反馈 + 权限护栏 + plan 评审 + skills + 模糊搜索
# + 并行对话 + 记忆 + worktree 管理等）
# MCP 用 Pi 内置扩展（读 ~/.pi/agent/mcp.json），不再装 pi-mcp-adapter。
PI_DEFAULT_PACKAGES=(
  "npm:pi-goal-x"
  "npm:pi-subagents"
  "npm:pi-powerline-footer"
  "npm:pi-web-access"
  # 两者都注册 web_search，后加载者生效，顺序不要调换
  "npm:pi-web-search"
  "npm:@juicesharp/rpiv-ask-user-question"
  "npm:pi-background-tasks"
  "npm:pi-simplify"
  "npm:billion-context"
  "npm:@langfuse/pi-observability-plugin"
  "npm:@juicesharp/rpiv-todo"
  "npm:pi-lens"
  "npm:@gotgenes/pi-permission-system"
  "npm:@plannotator/pi-extension"
  "npm:@dietrichgebert/ponytail"
  "npm:@ff-labs/pi-fff"
  "npm:pi-btw"
  "npm:pi-memory"
  "npm:@narumitw/pi-worktree"
)

# 常见 npm 全局 bin（mise / ~/.local）临时加入 PATH
_ensure_pi_path() {
  local d prefix
  prefix="$(npm prefix -g 2>/dev/null || true)"
  for d in "${prefix:+$prefix/bin}" "$HOME/.local/bin"; do
    if [[ -n "$d" && -d "$d" && ":$PATH:" != *":$d:"* ]]; then
      export PATH="$d:$PATH"
    fi
  done
}

# 安装/确保默认 pi packages（幂等）
install_pi_packages() {
  _ensure_pi_path

  if ! dotf_resolve_bin pi >/dev/null; then
    echo "✗ pi 未安装，无法安装 packages"
    return 1
  fi

  local pkg
  echo "正在确保 Pi packages..."
  for pkg in "${PI_DEFAULT_PACKAGES[@]}"; do
    echo "  → $pkg"
    if ! pi install "$pkg"; then
      echo "    镜像源失败，回退官方源重试: $pkg"
      if ! npm_config_registry=https://registry.npmjs.org pi install "$pkg"; then
        echo "✗ 安装失败: $pkg"
        return 1
      fi
    fi
  done

  echo "✓ Pi packages 已就绪"
}

install_pi() {
  local pi_bin
  _ensure_pi_path

  if pi_bin="$(dotf_resolve_bin pi)"; then
    echo "Pi 已安装: $pi_bin ($(pi --version 2>/dev/null || echo '?'))"
  else
    if ! command -v npm &>/dev/null; then
      echo "✗ 需要 Node.js/npm（Node ≥ 22.19）才能安装 Pi；请先: dotf sdk -i"
      return 1
    fi

    echo "正在安装 Pi coding agent（npm: @earendil-works/pi-coding-agent）..."
    if ! npm install -g @earendil-works/pi-coding-agent@latest; then
      echo "  当前镜像源安装失败，回退官方源重试..."
      if ! npm install -g @earendil-works/pi-coding-agent@latest --registry=https://registry.npmjs.org; then
        echo "✗ @earendil-works/pi-coding-agent 安装失败"
        return 1
      fi
    fi

    if command -v mise >/dev/null 2>&1; then
      mise reshim >/dev/null 2>&1 || true
    fi
    _ensure_pi_path

    if pi_bin="$(dotf_resolve_bin pi)"; then
      echo "✓ Pi 已就绪: $pi_bin"
    else
      echo "⚠️  安装完成但未找到 pi，请确认 npm 全局 bin 已在 PATH 中后重新打开终端"
      echo "  提示: npm prefix -g → 将其 /bin 加入 PATH"
      return 1
    fi
  fi

  install_pi_packages
}
