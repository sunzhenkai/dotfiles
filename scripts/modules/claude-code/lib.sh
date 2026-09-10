#!/bin/bash
# Claude Code CLI 安装（用户级）
#
# 背景：官方一键脚本 https://claude.ai/install.sh 挂在 Cloudflare 挑战后面，部分网络下
# curl 直接 403（`curl: (22) The requested URL returned error: 403`），重试无用。
#
# 安装策略（依次尝试，前者不可用才走后者）：
#   1. 官方安装脚本 —— 先下载到临时文件、确认是 shell 脚本再 `bash`。
#      不用 `curl | bash`，避免 200 + HTML（区域拦截页）被当脚本执行。
#   2. 官方分发仓库直装（官方 troubleshooting 文档给出的主机：downloads.claude.ai）
#        <base>/<channel>                    → 版本号（latest / stable）
#        <base>/<version>/manifest.json      → 各平台 sha256
#        <base>/<version>/<platform>/claude  → 原生二进制
#      落盘布局与官方脚本一致（自动更新依赖它）：
#        ~/.local/share/claude/versions/<version>  二进制
#        ~/.local/bin/claude                       → 该二进制
#   3. npm 包 @anthropic-ai/claude-code（需 Node.js 22+）
#
# 可调环境变量（仅直装路径）：
#   CLAUDE_CODE_CHANNEL     latest（默认）/ stable
#   CLAUDE_CODE_VERSION     指定具体版本，优先于 channel
#   CLAUDE_CODE_INSTALL_DIR 覆盖 ~/.local/share/claude
#   CLAUDE_CODE_BASE_URL    覆盖分发仓库地址
#
# 文档: https://docs.claude.com/en/docs/claude-code/setup
#       https://docs.claude.com/en/docs/claude-code/troubleshoot-install

source "$SCRIPT_DIR/scripts/lib/common.sh"

_ensure_claude_path() {
  local d="$HOME/.local/bin"
  if [[ -d "$d" && ":$PATH:" != *":$d:"* ]]; then
    export PATH="$d:$PATH"
  fi
}

_claude_code_channel() {
  printf '%s' "${CLAUDE_CODE_CHANNEL:-latest}"
}

# 官方脚本接受的实参：具体版本或 channel
_claude_code_version_spec() {
  printf '%s' "${CLAUDE_CODE_VERSION:-$(_claude_code_channel)}"
}

# 官方脚本优先：下载 → 确认是 shell 脚本 → 执行
# 返回 0=可用；1=拿不到/不是脚本/执行失败，交给直装路径
_claude_code_try_official() {
  local script rc
  script="$(mktemp)" || return 1

  # 403（如 Cloudflare 挑战）在这里就会失败；60s 上限覆盖脚本本身很小
  if ! curl -fsSL --connect-timeout 15 --max-time 60 -o "$script" https://claude.ai/install.sh; then
    echo "  ⚠ 官方安装脚本不可用（网络/403），改用官方分发仓库直装"
    rm -f "$script"
    return 1
  fi

  # 区域拦截页会以 200 返回 HTML，直接喂 bash 只会报语法错
  if [ ! -s "$script" ] || ! head -n 1 "$script" 2>/dev/null | grep -q '^#!'; then
    echo "  ⚠ 官方安装脚本返回的不是 shell 脚本（疑似区域拦截 HTML），改用官方分发仓库直装"
    rm -f "$script"
    return 1
  fi

  echo "  运行官方安装脚本（$(_claude_code_version_spec)）..."
  rc=0
  if command -v timeout >/dev/null 2>&1; then
    timeout 600 bash "$script" "$(_claude_code_version_spec)" || rc=$?
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout 600 bash "$script" "$(_claude_code_version_spec)" || rc=$?
  else
    bash "$script" "$(_claude_code_version_spec)" || rc=$?
  fi
  rm -f "$script"

  if [ "$rc" != 0 ]; then
    echo "  ⚠ 官方安装脚本执行失败（exit $rc），改用官方分发仓库直装"
    return 1
  fi
  _ensure_claude_path
  if command -v claude &>/dev/null || [ -x "$HOME/.local/bin/claude" ]; then
    return 0
  fi
  echo "  ⚠ 官方安装脚本结束但未找到 claude，改用官方分发仓库直装"
  return 1
}

_claude_code_install_dir() {
  printf '%s' "${CLAUDE_CODE_INSTALL_DIR:-$HOME/.local/share/claude}"
}

# Alpine 等 musl 发行版需要 -musl 构建
_claude_code_is_musl() {
  [ -f /etc/alpine-release ] && return 0
  local loader
  for loader in /lib/ld-musl-*.so.1; do
    [ -e "$loader" ] && return 0
  done
  return 1
}

# 官方 manifest 的平台键；不支持的平台返回 1
_claude_code_platform_key() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
  Darwin)
    case "$arch" in
    arm64 | aarch64) printf 'darwin-arm64' ;;
    x86_64)
      # Rosetta 2 下 uname 报 x64，但官方 x64 构建需要 AVX，优先原生 arm64
      if [ "$(sysctl -n sysctl.proc_translated 2>/dev/null)" = "1" ]; then
        printf 'darwin-arm64'
      else
        printf 'darwin-x64'
      fi
      ;;
    *) return 1 ;;
    esac
    ;;
  Linux)
    case "$arch" in
    x86_64 | amd64) arch=x64 ;;
    aarch64 | arm64) arch=arm64 ;;
    *) return 1 ;;
    esac
    if _claude_code_is_musl; then
      printf 'linux-%s-musl' "$arch"
    else
      printf 'linux-%s' "$arch"
    fi
    ;;
  *) return 1 ;;
  esac
}

# channel/version → 版本号；取不到返回 1
_claude_code_resolve_version() {
  local base="$1" channel="$2" version
  if [ -n "${CLAUDE_CODE_VERSION:-}" ]; then
    printf '%s' "$CLAUDE_CODE_VERSION"
    return 0
  fi
  version="$(curl -fsSL --max-time 30 "$base/$channel" 2>/dev/null)" || return 1
  version="$(printf '%s' "$version" | tr -d '[:space:]')"
  case "$version" in
  [0-9]*.[0-9]*) printf '%s' "$version" ;;
  *) return 1 ;;
  esac
}

# 从 manifest.json 取平台 sha256；取不到返回 1
_claude_code_manifest_checksum() {
  local manifest="$1" platform="$2"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$manifest" "$platform" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        manifest = json.load(fh)
    print(manifest["platforms"][sys.argv[2]]["checksum"])
except Exception:
    raise SystemExit(1)
PY
}

_claude_code_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    return 1
  fi
}

# 能跑起来才算装好（挡掉 musl/glibc、CPU 架构选错这类"装了但不可用"）
_claude_code_smoke_test() {
  local bin="$1" out
  if command -v timeout >/dev/null 2>&1; then
    out="$(timeout 20 "$bin" --version 2>/dev/null)" || return 1
  elif command -v gtimeout >/dev/null 2>&1; then
    out="$(gtimeout 20 "$bin" --version 2>/dev/null)" || return 1
  else
    out="$("$bin" --version 2>/dev/null)" || return 1
  fi
  [ -n "$out" ]
}

# 返回 0=装好 1=源不可用（可回退 npm） 2=完整性校验失败（不回退）
_claude_code_install_native() {
  local base platform channel dir staged version url manifest expected actual rc=1
  platform="$(_claude_code_platform_key)" || {
    echo "  ⚠ 不支持的平台: $(uname -s) $(uname -m)"
    return 1
  }
  base="${CLAUDE_CODE_BASE_URL:-https://downloads.claude.ai/claude-code-releases}"
  channel="$(_claude_code_channel)"
  dir="$(_claude_code_install_dir)"
  mkdir -p "$dir/versions" "$HOME/.local/bin" || return 1
  staged="$dir/versions/.claude.part.$$"
  # 清理中断留下的半成品（不动当天其它进程正在写的 part）
  find "$dir/versions" -maxdepth 1 -name '.claude.part.*' -mtime +1 -exec rm -f {} + 2>/dev/null || true

  version="$(_claude_code_resolve_version "$base" "$channel")" || {
    echo "  ⚠ 无法从 $base 获取 $channel 版本号"
    return 1
  }
  url="$base/$version/$platform/claude"
  echo "  下载 claude $version ($platform)（约 200MB，静默下载）"
  # 慢于 1KB/s 持续 30s 视为卡死，避免 dotf 里挂住
  if ! curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 \
    --speed-limit 1024 --speed-time 30 -o "$staged" "$url"; then
    echo "  ⚠ 下载失败: $url"
    rm -f "$staged"
    return 1
  fi

  expected=""
  manifest="$staged.manifest"
  if curl -fsSL --max-time 30 -o "$manifest" "$base/$version/manifest.json" 2>/dev/null; then
    expected="$(_claude_code_manifest_checksum "$manifest" "$platform")" || expected=""
  fi
  rm -f "$manifest"

  if [ -n "$expected" ]; then
    if actual="$(_claude_code_sha256 "$staged")"; then
      if [ "$actual" != "$expected" ]; then
        echo "✗ sha256 校验失败: $url"
        echo "  期望 $expected"
        echo "  实际 $actual"
        rm -f "$staged"
        return 2
      fi
      echo "  ✓ sha256 校验通过"
    else
      echo "✗ 缺少 sha256sum/shasum，无法校验二进制，已中止"
      rm -f "$staged"
      return 2
    fi
  else
    echo "  ⚠ 未取到 manifest.json，跳过 sha256 校验"
  fi

  if ! chmod 755 "$staged"; then
    rm -f "$staged"
    return 1
  fi
  if ! _claude_code_smoke_test "$staged"; then
    echo "  ⚠ 二进制无法执行，平台构建可能不匹配: $platform"
    rm -f "$staged"
    return 1
  fi
  if ! mv -f "$staged" "$dir/versions/$version"; then
    rm -f "$staged"
    return 1
  fi
  if ! ln -sfn "$dir/versions/$version" "$HOME/.local/bin/claude"; then
    echo "  ⚠ 无法创建 $HOME/.local/bin/claude 软链"
    return 1
  fi
  echo "  ✓ 已安装 $dir/versions/$version"
  return 0
}

# 官方备选：npm 包（需 Node.js 22+）
_claude_code_install_npm() {
  local npm_bin
  if ! command -v npm &>/dev/null; then
    echo "  备选: npm install -g @anthropic-ai/claude-code（需先 dotf sdk -i）"
    return 1
  fi

  echo "  改用 npm 安装 @anthropic-ai/claude-code@latest ..."
  if ! npm install -g @anthropic-ai/claude-code@latest; then
    echo "  ⚠ npm 安装失败"
    return 1
  fi

  npm_bin="$(npm prefix -g 2>/dev/null)/bin"
  if [[ -d "$npm_bin" && ":$PATH:" != *":$npm_bin:"* ]]; then
    export PATH="$npm_bin:$PATH"
  fi
  _ensure_claude_path

  if command -v claude &>/dev/null; then
    echo "✓ Claude Code CLI 已就绪（npm）: $(command -v claude)"
    return 0
  fi
  echo "⚠️  npm 安装完成但未找到 claude，请确认 npm 全局 bin 在 PATH 中"
  return 1
}

# 装机后统一收尾
_claude_code_report_ready() {
  local label="$1"
  _ensure_claude_path
  if command -v claude &>/dev/null; then
    echo "✓ Claude Code CLI 已就绪（$label）: $(command -v claude)"
    return 0
  fi
  if [ -x "$HOME/.local/bin/claude" ]; then
    echo "✓ Claude Code CLI 已就绪（$label）: $HOME/.local/bin/claude"
    echo "  提示: zsh/modules/paths.zsh 已加载 ~/.local/bin"
    return 0
  fi
  echo "⚠️  安装完成但未找到 claude，请确认 ~/.local/bin 已在 PATH 中后重新打开终端"
  return 1
}

install_claude_code() {
  local rc

  _ensure_claude_path

  if command -v claude &>/dev/null; then
    echo "Claude Code CLI 已安装: $(command -v claude) ($(claude --version 2>/dev/null || echo '?'))"
    return 0
  fi

  echo "正在安装 Claude Code CLI（官方脚本优先，失败回退官方分发仓库）..."
  if _claude_code_try_official; then
    _claude_code_report_ready "官方脚本"
    return $?
  fi

  _claude_code_install_native
  rc=$?
  if [ "$rc" = 2 ]; then
    echo "✗ Claude Code CLI 安装失败：二进制完整性校验未通过，已中止"
    return 1
  fi
  if [ "$rc" = 0 ]; then
    _claude_code_report_ready "分发仓库原生二进制"
    return $?
  fi

  echo "✗ Claude Code CLI 原生安装失败（官方源不可达）"
  if _claude_code_install_npm; then
    return 0
  fi
  echo "  其他方式: macOS → brew install --cask claude-code"
  echo "  手动安装说明: https://docs.claude.com/en/docs/claude-code/setup"
  return 1
}
