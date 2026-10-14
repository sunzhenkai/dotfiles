#!/bin/bash
# 公共工具函数

# ============================================================
# 计时工具函数（兼容 Bash 3.2+，不使用关联数组）
# ============================================================

# 计时数据存储（平行数组）
_timing_names=()
_timing_durations=()
_timing_statuses=()
_timing_count=0

# 将秒数格式化为可读字符串
# 参数: $1=秒数（整数）
# 输出: "Xm Ys" 或 "Xs"
timer_format() {
  local seconds="${1:-0}"
  if (( seconds >= 60 )); then
    local minutes=$(( seconds / 60 ))
    local secs=$(( seconds % 60 ))
    echo "${minutes}m ${secs}s"
  else
    echo "${seconds}s"
  fi
}

# 记录一次计时结果
# 参数: $1=模块名, $2=耗时秒数, $3=状态(✓/✗)
_timing_record() {
  _timing_names+=("$1")
  _timing_durations+=("$2")
  _timing_statuses+=("$3")
  _timing_count=$(( _timing_count + 1 ))
}

# 输出汇总表格
print_timing_summary() {
  if [[ $_timing_count -eq 0 ]]; then
    return 0
  fi

  local total_seconds=0
  local success_count=0

  echo ""
  echo "========================================"
  echo "  安装耗时统计"
  echo "========================================"

  local i
  for (( i = 0; i < _timing_count; i++ )); do
    local name="${_timing_names[$i]}"
    local duration="${_timing_durations[$i]}"
    local status="${_timing_statuses[$i]}"
    local formatted
    formatted=$(timer_format "$duration")

    printf "  %-14s %-10s %s\n" "$name" "$formatted" "$status"

    total_seconds=$(( total_seconds + duration ))
    if [[ "$status" == "✓" ]]; then
      success_count=$(( success_count + 1 ))
    fi
  done

  echo "----------------------------------------"
  local total_formatted
  total_formatted=$(timer_format "$total_seconds")
  printf "  %-14s %-10s %d/%d 成功\n" "总计" "$total_formatted" "$success_count" "$_timing_count"
  echo "========================================"
}

# ============================================================
# Python 包安装兼容函数
# ============================================================

# 安装 Python 包，兼容 PEP 668
# 参数: $1=包名 (可带版本约束，如 "mysqlclient>=2.0")
# 行为: 优先使用 uv pip install --system，回退到 pip3 install --break-system-packages
pip_install_system() {
  local pkg="$1"
  if [ -z "$pkg" ]; then
    echo "⚠️  pip_install_system: 未指定包名"
    return 1
  fi

  echo "Installing Python package: $pkg"

  # 优先使用 uv（已在 homebrew 模块中安装）
  if command -v uv &>/dev/null; then
    echo "  Using uv pip install --system ..."
    if uv pip install --system "$pkg"; then
      echo "  ✓ Installed via uv: $pkg"
      return 0
    fi
    echo "  ⚠️  uv pip install failed, falling back to pip3 ..."
  fi

  # 回退到 pip3，带 --break-system-packages 标志
  if command -v pip3 &>/dev/null; then
    echo "  Using pip3 install --break-system-packages ..."
    if pip3 install --break-system-packages "$pkg"; then
      echo "  ✓ Installed via pip3: $pkg"
      return 0
    fi
    echo "  ⚠️  pip3 install also failed"
  fi

  # 最终失败
  echo "  ⚠️  Failed to install $pkg — neither uv nor pip3 succeeded"
  echo "  You can try manually: uv pip install --system $pkg"
  return 1
}

# ============================================================
# 确认函数
# ============================================================

# 确认函数（提示与输入均走 /dev/tty，避免被 runner 捕获 stdout/stderr 时不可见）
# 参数: $1=提示信息, $2=默认值(Y/N, 默认Y)
# 返回: 0=用户确认, 1=用户拒绝
#
# /dev/tty 可用性检测：仅 [-r/-w] 查 file mode 不够，PTY-less 会话仍 ENXIO。
# 需用真打开 FD 试探两次（read+write）才能可靠识别。
is_tty_available() {
  if ! exec 3</dev/tty 2>/dev/null; then
    return 1
  fi
  exec 3<&-
  if ! exec 3>/dev/tty 2>/dev/null; then
    return 1
  fi
  exec 3>&-
  return 0
}

confirm() {
  local prompt="$1"
  local default="${2:-Y}"

  # 顶层 orchestrator 已通过 --yes 授权时，模块内不再二次确认
  if [ "${DOTF_YES:-0}" = "1" ] || [ "${ASSUME_YES:-0}" = "1" ]; then
    return 0
  fi

  if ! is_tty_available; then
    echo "错误: 非 TTY 环境请使用 --yes 或 --dry-run" >&2
    return 1
  fi

  local reply=""
  if [[ "$default" == "Y" ]]; then
    printf '%s [Y/n]: ' "$prompt" >/dev/tty
    read -r reply </dev/tty || reply=""
    [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
  else
    printf '%s [y/N]: ' "$prompt" >/dev/tty
    read -r reply </dev/tty || reply=""
    [[ "$reply" =~ ^[Yy] ]]
  fi
}

# ============================================================
# tmux-yank 剪贴板依赖
# ============================================================

# 是否已有可用的系统剪贴板命令（供 tmux-yank 使用）
has_clipboard_tool() {
  command -v pbcopy &>/dev/null ||
    command -v wl-copy &>/dev/null ||
    command -v xsel &>/dev/null ||
    command -v xclip &>/dev/null ||
    command -v clip.exe &>/dev/null ||
    command -v putclip &>/dev/null
}

# 安装 tmux-yank 所需剪贴板工具（Linux: xclip/xsel/wl-clipboard；macOS 自带 pbcopy）
# 无交互确认；已具备工具时直接跳过。
install_tmux_clipboard_deps() {
  if has_clipboard_tool; then
    echo "剪贴板工具已就绪（tmux-yank）"
    return 0
  fi

  # macOS 自带 pbcopy；若走到这里说明环境异常
  if [[ "$OSTYPE" =~ ^darwin ]]; then
    echo "⚠️  macOS 应自带 pbcopy，跳过剪贴板依赖安装"
    return 0
  fi

  echo "正在安装 tmux-yank 剪贴板依赖（xclip/xsel/wl-clipboard）..."

  local os_id=""
  if [ -f "/etc/os-release" ]; then
    # shellcheck source=/dev/null
    os_id=$(. /etc/os-release && echo "$ID")
  elif [ -f "/etc/arch-release" ]; then
    os_id="arch"
  fi

  case "$os_id" in
  ubuntu | debian | pop | linuxmint)
    sudo apt-get update
    sudo apt-get install -y xclip xsel wl-clipboard
    ;;
  arch | manjaro | endeavouros)
    sudo pacman -Sy --noconfirm xclip xsel wl-clipboard
    ;;
  fedora)
    sudo dnf install -y xclip xsel wl-clipboard
    ;;
  rhel | centos | rocky | almalinux | alinux | amzn)
    if command -v dnf &>/dev/null; then
      sudo dnf install -y xclip xsel || sudo dnf install -y xclip
      sudo dnf install -y wl-clipboard 2>/dev/null || true
    else
      sudo yum install -y xclip xsel || sudo yum install -y xclip
    fi
    ;;
  *)
    if command -v brew &>/dev/null; then
      brew install xclip 2>/dev/null || true
    else
      echo "⚠️  未识别的系统 ($os_id)，请手动安装 xclip / xsel / wl-clipboard"
      return 1
    fi
    ;;
  esac

  if has_clipboard_tool; then
    echo "✓ tmux-yank 剪贴板依赖已安装"
    return 0
  fi

  echo "⚠️  剪贴板依赖安装后仍未检测到工具，请手动检查"
  return 1
}

# ============================================================
# 远程安装脚本：下载到临时文件 → 校验 → 执行（禁止 curl | sh）
# ============================================================

# 计算文件 sha256（macOS: shasum；Linux: sha256sum）
_dotf_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    return 1
  fi
}

# 用法: dotf_fetch_run [--sha256 HEX] [--interp sh|bash] URL [脚本参数...]
# - 仅允许 https（--proto '=https'，重定向同样受限），-f 让 HTTP 错误直接失败
# - 下载内容必须非空且以 #! 开头（挡住 200 + HTML 拦截页）
# - 给定 --sha256 时不匹配即拒绝执行；URL 中可自行写死 tag/commit 以固定版本
dotf_fetch_run() {
  local sha="" interp="bash" url script actual rc
  while [ $# -gt 0 ]; do
    case "$1" in
      --sha256) sha="$2"; shift 2 ;;
      --interp) interp="$2"; shift 2 ;;
      *) break ;;
    esac
  done
  url="${1:-}"
  if [ -z "$url" ]; then
    echo "✗ dotf_fetch_run: 缺少 URL" >&2
    return 2
  fi
  shift
  case "$url" in
    https://*) ;;
    *) echo "✗ dotf_fetch_run: 仅允许 https URL: $url" >&2; return 2 ;;
  esac

  script="$(mktemp "${TMPDIR:-/tmp}/dotf-fetch.XXXXXX")" || return 1
  if ! curl -fsSL --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 300 -o "$script" "$url"; then
    echo "✗ 下载失败: $url" >&2
    rm -f "$script"
    return 1
  fi
  if [ ! -s "$script" ] || ! head -n 1 "$script" | grep -q '^#!'; then
    echo "✗ 下载内容不是 shell 脚本（疑似拦截页）: $url" >&2
    rm -f "$script"
    return 1
  fi
  if [ -n "$sha" ]; then
    actual="$(_dotf_sha256 "$script")" || {
      echo "✗ 无 sha256sum/shasum，无法校验: $url" >&2
      rm -f "$script"
      return 1
    }
    if [ "$actual" != "$sha" ]; then
      echo "✗ sha256 不匹配: $url (期望 $sha，实际 $actual)" >&2
      rm -f "$script"
      return 1
    fi
  fi

  rc=0
  "$interp" "$script" "$@" || rc=$?
  rm -f "$script"
  return "$rc"
}

# ============================================================
# Homebrew 定位（唯一真相源：其它脚本不要再写死前缀）
# ============================================================
DOTF_BREW_CANDIDATES=(
  "/opt/homebrew/bin/brew"              # macOS Apple Silicon
  "/usr/local/bin/brew"                 # macOS Intel
  "/home/linuxbrew/.linuxbrew/bin/brew" # Linux
)

# 输出 brew 可执行文件路径；找不到返回 1
dotf_brew_bin() {
  local b
  if b="$(command -v brew 2>/dev/null)" && [ -n "$b" ]; then
    echo "$b"
    return 0
  fi
  for b in "${DOTF_BREW_CANDIDATES[@]}"; do
    if [ -x "$b" ]; then
      echo "$b"
      return 0
    fi
  done
  return 1
}

# 输出 brew 前缀（优先 brew --prefix）；找不到返回 1
dotf_brew_prefix() {
  local b
  b="$(dotf_brew_bin)" || return 1
  "$b" --prefix 2>/dev/null || dirname "$(dirname "$b")"
}
