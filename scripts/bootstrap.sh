#!/usr/bin/env bash
# 最小 bootstrap：不读取 modules.yaml，仅预检基础运行时并委托 dotf init
# 用法: scripts/bootstrap.sh [--check-only] [--yes] [--os <id>] [dotf init 参数...]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOTF_BIN="${DOTF_BIN:-$ROOT/bin/dotf}"

# 支持平台族（与 design 前置矩阵对齐）
# - debian/ubuntu: apt + python3 + python3-yaml
# - fedora/rhel/centos: dnf/yum + python3 + python3-pyyaml
# - arch: pacman + python + python-yaml
# - darwin: python3 + pip/brew PyYAML
# 基础命令: bash, git, curl|wget, python3

CHECK_ONLY=0
ASSUME_YES=0
FORCE_OS=""
INIT_ARGS=()

usage() {
  cat <<'EOF'
用法: scripts/bootstrap.sh [选项] [--] [dotf init 参数...]

最小运行时预检（不读取 modules.yaml），依赖齐全后委托 bin/dotf init。

选项:
  --check-only    仅预检，不安装依赖、不调用 init
  --yes           缺失依赖时自动确认安装（非交互）
  --os <id>       覆盖 OS 检测（ubuntu|debian|fedora|rhel|arch|darwin|...）
  -h, --help      显示帮助

示例:
  scripts/bootstrap.sh
  scripts/bootstrap.sh --check-only
  scripts/bootstrap.sh --yes -- --list
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
  --check-only)
    CHECK_ONLY=1
    ;;
  --yes | -y)
    ASSUME_YES=1
    ;;
  --os)
    shift
    FORCE_OS="${1:-}"
    if [ -z "$FORCE_OS" ]; then
      echo "错误: --os 需要参数" >&2
      exit 2
    fi
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  --)
    shift
    INIT_ARGS+=("$@")
    break
    ;;
  *)
    INIT_ARGS+=("$1")
    ;;
  esac
  shift
done

log() {
  printf '%s\n' "$*"
}

# 绝不打印环境变量值或凭据
log_missing() {
  printf '缺失: %s\n' "$1"
}

detect_os() {
  if [ -n "${DOTF_BOOTSTRAP_OS:-}" ]; then
    printf '%s\n' "$DOTF_BOOTSTRAP_OS"
    return 0
  fi
  if [ -n "$FORCE_OS" ]; then
    printf '%s\n' "$FORCE_OS"
    return 0
  fi
  if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    printf '%s\n' "${ID:-unknown}"
    return 0
  fi
  if [ "$(uname -s 2>/dev/null || true)" = "Darwin" ]; then
    printf '%s\n' "darwin"
    return 0
  fi
  printf '%s\n' "unknown"
}

os_family() {
  case "$1" in
  ubuntu | debian | linuxmint | pop)
    printf '%s\n' "debian"
    ;;
  fedora | rhel | centos | rocky | alma | amzn)
    printf '%s\n' "rhel"
    ;;
  arch | manjaro | endeavouros)
    printf '%s\n' "arch"
    ;;
  darwin)
    printf '%s\n' "darwin"
    ;;
  unknown | "")
    printf '%s\n' "unsupported"
    ;;
  *)
    # 未知但非空：仍标为 unsupported，避免误装
    printf '%s\n' "unsupported"
    ;;
  esac
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

have_python() {
  have_cmd python3
}

have_pyyaml() {
  have_python || return 1
  python3 -c 'import yaml' >/dev/null 2>&1
}

have_fetcher() {
  have_cmd curl || have_cmd wget
}

# 收集缺失项到全局字符串（空格分隔标签）
MISSING=""

check_runtime() {
  MISSING=""
  have_cmd bash || MISSING="$MISSING bash"
  have_cmd git || MISSING="$MISSING git"
  have_fetcher || MISSING="$MISSING curl|wget"
  have_python || MISSING="$MISSING python3"
  if have_python; then
    have_pyyaml || MISSING="$MISSING PyYAML"
  fi
  # trim
  MISSING="$(printf '%s' "$MISSING" | sed 's/^ *//')"
}

print_guidance() {
  local family="$1"
  log "请安装缺失依赖后重试。平台建议："
  case "$family" in
  debian)
    log "  sudo apt-get update"
    log "  sudo apt-get install -y bash git curl python3 python3-yaml"
    ;;
  rhel)
    if have_cmd dnf; then
      log "  sudo dnf install -y bash git curl python3 python3-pyyaml"
    else
      log "  sudo yum install -y bash git curl python3 python3-pyyaml"
    fi
    ;;
  arch)
    log "  sudo pacman -Sy --needed bash git curl python python-yaml"
    ;;
  darwin)
    log "  # 需要 Homebrew 或官方 Python"
    log "  brew install python git || true"
    log "  python3 -m pip install --user PyYAML"
    ;;
  *)
    log "  当前平台未提供自动安装命令。"
    log "  请手动安装: bash, git, curl 或 wget, python3, PyYAML"
    ;;
  esac
}

confirm_install() {
  if [ "$ASSUME_YES" -eq 1 ]; then
    return 0
  fi
  if [ ! -t 0 ]; then
    log "非交互环境：请使用 --yes 确认安装，或手动安装依赖后重试。"
    return 1
  fi
  local reply=""
  printf '是否按上述建议尝试安装缺失依赖? [y/N]: '
  read -r reply || true
  case "$reply" in
  y | Y | yes | YES) return 0 ;;
  *) return 1 ;;
  esac
}

try_install_deps() {
  local family="$1"
  case "$family" in
  debian)
    sudo apt-get update
    sudo apt-get install -y bash git curl python3 python3-yaml
    ;;
  rhel)
    if have_cmd dnf; then
      sudo dnf install -y bash git curl python3 python3-pyyaml
    else
      sudo yum install -y bash git curl python3 python3-pyyaml
    fi
    ;;
  arch)
    sudo pacman -Sy --needed --noconfirm bash git curl python python-yaml
    ;;
  darwin)
    if have_cmd brew; then
      brew install python git || true
    fi
    python3 -m pip install --user PyYAML
    ;;
  *)
    log "错误: 不支持的平台，无法自动安装" >&2
    return 1
    ;;
  esac
}

# ---- main ----

OS_ID="$(detect_os)"
FAMILY="$(os_family "$OS_ID")"

log "bootstrap: 检测 OS=$OS_ID (family=$FAMILY)"

if [ "$FAMILY" = "unsupported" ]; then
  log "错误: 无法识别或不支持的平台 ($OS_ID)" >&2
  log "请手动安装前置条件: bash, git, curl|wget, python3, PyYAML" >&2
  exit 1
fi

check_runtime

if [ -n "$MISSING" ]; then
  for item in $MISSING; do
    log_missing "$item"
  done
  print_guidance "$FAMILY"

  if [ "$CHECK_ONLY" -eq 1 ]; then
    exit 1
  fi

  if ! confirm_install; then
    log "已取消安装。请手动安装依赖后重试。"
    exit 1
  fi

  log "开始安装缺失依赖…"
  try_install_deps "$FAMILY"
  check_runtime
  if [ -n "$MISSING" ]; then
    log "错误: 安装后仍缺失: $MISSING" >&2
    exit 1
  fi
fi

log "✓ 基础运行时就绪"

if [ "$CHECK_ONLY" -eq 1 ]; then
  exit 0
fi

if [ ! -x "$DOTF_BIN" ]; then
  log "错误: 找不到 dotf: $DOTF_BIN" >&2
  exit 1
fi

if [ ${#INIT_ARGS[@]} -gt 0 ]; then
  log "委托: dotf init（透传 ${#INIT_ARGS[@]} 个参数）"
  exec "$DOTF_BIN" init "${INIT_ARGS[@]}"
else
  log "委托: dotf init"
  exec "$DOTF_BIN" init
fi
