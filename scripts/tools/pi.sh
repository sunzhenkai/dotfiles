#!/bin/bash
# Pi coding agent CLI 安装
# 官方文档: https://pi.dev/docs/latest/
# 包: @earendil-works/pi-coding-agent

source "$SCRIPT_DIR/scripts/tools/common.sh"

# 默认扩展包（目标管理 + 子代理委派）
PI_DEFAULT_PACKAGES=(
  "npm:@ogulcancelik/pi-goal"
  "npm:@virdis/subagents"
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

# 上游 @virdis/subagents 0.1.0 的 SKILL.md 写成 `name: @virdis/subagents`：
# 1) YAML 中 @ 为保留字符，pi 启动时报 [Skill conflicts]
# 2) pi skill name 规范只允许 [a-z0-9-]
# 重装 packages 后会覆盖，故安装后幂等修补。
_patch_virdis_subagents_skill() {
  local skill="$HOME/.pi/agent/npm/node_modules/@virdis/subagents/skills/pi-subagents/SKILL.md"
  [[ -f "$skill" ]] || return 0

  if grep -qE '^name: @virdis/subagents$' "$skill"; then
    sed -i 's/^name: @virdis\/subagents$/name: pi-subagents/' "$skill"
    echo "  → 已修补 @virdis/subagents skill name → pi-subagents（上游 YAML 非法）"
  fi
}

# 安装/确保默认 pi packages（幂等）
install_pi_packages() {
  _ensure_pi_path

  if ! command -v pi &>/dev/null; then
    echo "✗ pi 未安装，无法安装 packages"
    return 1
  fi

  local pkg
  echo "正在确保 Pi packages..."
  for pkg in "${PI_DEFAULT_PACKAGES[@]}"; do
    echo "  → $pkg"
    if ! pi install "$pkg"; then
      echo "✗ 安装失败: $pkg"
      return 1
    fi
  done

  _patch_virdis_subagents_skill
  echo "✓ Pi packages 已就绪"
}

install_pi() {
  _ensure_pi_path

  if command -v pi &>/dev/null; then
    echo "Pi 已安装: $(command -v pi) ($(pi --version 2>/dev/null || echo '?'))"
  else
    if ! command -v npm &>/dev/null; then
      echo "✗ 需要 Node.js/npm（Node ≥ 22.19）才能安装 Pi；请先: dotf sdk -i"
      return 1
    fi

    echo "正在安装 Pi coding agent（官方 install.sh）..."
    # 无 TTY 时官方脚本会自动确认 install，不阻塞 CI/非交互
    curl -fsSL https://pi.dev/install.sh | sh

    _ensure_pi_path

    if command -v pi &>/dev/null; then
      echo "✓ Pi 已就绪: $(command -v pi)"
    else
      echo "⚠️  安装完成但未找到 pi，请确认 npm 全局 bin 已在 PATH 中后重新打开终端"
      echo "  提示: npm prefix -g → 将其 /bin 加入 PATH"
      return 1
    fi
  fi

  install_pi_packages
}
