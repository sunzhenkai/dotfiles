#!/bin/bash
# OmO 独立版（omo）安装
# 上游: https://github.com/code-yeongyu/oh-my-openagent（npm 包 omo-ai）
# 官方安装脚本: https://get.omo.dev/install.sh —— 下载原生二进制到 ~/.local/bin，
# 按发布附带的 SHA256SUMS 校验；实参可为 latest | beta | X.Y.Z。
#
# OMO_NO_MODIFY_PATH=1：不让自己往 shell profile 写 PATH，PATH 由本仓
# config/shell/zsh/modules/paths.zsh 管理。

source "$SCRIPT_DIR/scripts/lib/common.sh"

# 安装器落位 ~/.local/bin，临时确保在 PATH（新终端由 paths.zsh 加载）
_ensure_omo_path() {
  local d="$HOME/.local/bin"
  if [[ -d "$d" && ":$PATH:" != *":$d:"* ]]; then
    export PATH="$d:$PATH"
  fi
}

install_omo() {
  local version="${OMO_VERSION:-latest}" script rc
  script="$(mktemp)" || return 1

  echo "正在安装 OmO 独立版（omo ${version}）..."
  # 先落盘再执行：下载失败或返回拦截页时不会把半截内容喂给 bash
  if ! curl -fsSL --connect-timeout 15 --max-time 60 -o "$script" https://get.omo.dev/install.sh; then
    echo "  ⚠ 下载安装脚本失败"
    rm -f "$script"
    return 1
  fi
  if [ ! -s "$script" ] || ! head -n 1 "$script" 2>/dev/null | grep -q '^#!'; then
    echo "  ⚠ 下载内容不是 shell 脚本"
    rm -f "$script"
    return 1
  fi

  rc=0
  OMO_NO_MODIFY_PATH=1 bash "$script" "$version" || rc=$?
  rm -f "$script"
  if [ "$rc" != 0 ]; then
    echo "  ⚠ 安装脚本执行失败（exit $rc）"
    return 1
  fi

  _ensure_omo_path
  if command -v omo &>/dev/null || [[ -x "$HOME/.local/bin/omo" ]]; then
    echo "✓ omo 已就绪: $(command -v omo 2>/dev/null || echo "$HOME/.local/bin/omo") ($(omo --version 2>/dev/null || echo '?'))"
    return 0
  fi
  echo "⚠️  安装完成但未找到 omo，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
  return 1
}
