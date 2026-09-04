#!/usr/bin/env bash
# 公共配置安全库：Bash 3.2 兼容入口；复杂安全操作委托 scripts/dotf_core。
# 依赖: HOME、python3；可选 DOTFILES_ROOT、DOTF_TARGET_ROOT、DOTF_RUN_ID。

: "${DOTF_BACKUP_DIR:=${HOME}/.config/backups}"
: "${DOTF_TARGET_ROOT:=${HOME}}"

_DOTF_CONFIG_SAFE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
_DOTF_CORE_PYTHONPATH=$(cd "${_DOTF_CONFIG_SAFE_DIR}/.." && pwd)

_dotf_core() {
  if [ -n "${PYTHONPATH:-}" ]; then
    PYTHONPATH="${_DOTF_CORE_PYTHONPATH}:${PYTHONPATH}" python3 -m dotf_core.cli "$@"
  else
    PYTHONPATH="${_DOTF_CORE_PYTHONPATH}" python3 -m dotf_core.cli "$@"
  fi
}

if [ -z "${DOTF_RUN_ID:-}" ]; then
  DOTF_RUN_ID=$(_dotf_core run-id) || return 1 2>/dev/null || exit 1
fi

# 展开 ~/ 与相对路径（不 resolve symlink）
dotf_expand_path() {
  local p="$1"
  if [ -z "$p" ]; then
    printf '\n'
    return 0
  fi
  if [ "$p" = "~" ]; then
    p="$HOME"
  elif [ "${p#"~/"}" != "$p" ]; then
    p="${HOME}/${p#"~/"}"
  fi
  printf '%s\n' "$p"
}

# 逐级 no-follow 地创建父目录。
dotf_ensure_parent() {
  _dotf_core ensure-parent "$DOTF_TARGET_ROOT" "$1" >/dev/null
}

# 显式路径边界检查；叶子默认也不得为软链。
dotf_safe_path_check() {
  local root="$1"
  local target="$2"
  local allow_leaf="${3:-0}"
  if [ "$allow_leaf" = "1" ]; then
    _dotf_core path-check "$root" "$target" --allow-leaf-symlink >/dev/null
  else
    _dotf_core path-check "$root" "$target" >/dev/null
  fi
}

# 生成 run-id + target-relative-path + hash 的备份目标（只计算，不预留）。
dotf_backup_dest() {
  _dotf_core backup-dest "$1" "$DOTF_BACKUP_DIR" "$DOTF_RUN_ID" "$DOTF_TARGET_ROOT"
}

# no-follow 备份并移除原目录项；第二参数 1 表示敏感文件。
dotf_backup_to() {
  local src="$1"
  local sensitive="${2:-0}"
  if [ "$sensitive" = "1" ]; then
    _dotf_core backup "$src" "$DOTF_BACKUP_DIR" "$DOTF_RUN_ID" "$DOTF_TARGET_ROOT" --sensitive --remove-source
  else
    _dotf_core backup "$src" "$DOTF_BACKUP_DIR" "$DOTF_RUN_ID" "$DOTF_TARGET_ROOT" --remove-source
  fi
}

# 将调用方生成的文件安全写入目标。输出 changed/unchanged。
# 用法: dotf_atomic_write_file <staged-source> <target> [json|yaml|toml|text] [mode] [sensitive]
dotf_atomic_write_file() {
  local source="$1"
  local target="$2"
  local format="${3:-text}"
  local mode="${4:-600}"
  local sensitive="${5:-0}"
  if [ "$sensitive" = "1" ]; then
    _dotf_core atomic-write-file "$source" "$target" "$DOTF_TARGET_ROOT" \
      --format "$format" --mode "$mode" --backup-root "$DOTF_BACKUP_DIR" \
      --run-id "$DOTF_RUN_ID" --sensitive
  else
    _dotf_core atomic-write-file "$source" "$target" "$DOTF_TARGET_ROOT" \
      --format "$format" --mode "$mode" --backup-root "$DOTF_BACKUP_DIR" \
      --run-id "$DOTF_RUN_ID"
  fi
}

# 统一终端文本脱敏入口。
dotf_sanitize() {
  if [ "$#" -gt 0 ]; then
    _dotf_core sanitize "$1"
  else
    _dotf_core sanitize
  fi
}

# 解析期望源的绝对路径（用于比较）
dotf_resolve_source() {
  local source="$1"
  local expected
  case "$source" in
  /*) expected="$source" ;;
  *)
    if [ -z "${DOTFILES_ROOT:-}" ]; then
      echo "dotf_resolve_source: 相对源需要 DOTFILES_ROOT" >&2
      return 2
    fi
    expected="${DOTFILES_ROOT}/${source}"
    ;;
  esac
  if command -v realpath >/dev/null 2>&1; then
    realpath "$expected" 2>/dev/null || printf '%s\n' "$expected"
  else
    readlink -f "$expected" 2>/dev/null || printf '%s\n' "$expected"
  fi
}

# 当前 symlink 指向（尽量绝对化）
dotf_readlink_target() {
  local path="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$path" 2>/dev/null || readlink "$path"
  else
    readlink -f "$path" 2>/dev/null || readlink "$path"
  fi
}

# 确保 target 为指向 source 的 symlink。保持旧调用和 DOTF_CFG_STATUS 语义。
dotf_ensure_symlink() {
  local source="$1"
  local target="$2"
  local expected_link expected_abs current
  local reason=""

  target=$(dotf_expand_path "$target")
  case "$source" in
  /*) expected_link="$source" ;;
  *) expected_link="${DOTFILES_ROOT}/${source}" ;;
  esac
  expected_abs=$(dotf_resolve_source "$source")

  dotf_ensure_parent "$target"
  # 允许现有叶子是链接，但任何父目录链接都 fail-closed。
  dotf_safe_path_check "$DOTF_TARGET_ROOT" "$target" 1

  if [ -L "$target" ]; then
    current=$(dotf_readlink_target "$target")
    if [ "$current" = "$expected_abs" ] || [ "$current" = "$expected_link" ]; then
      DOTF_CFG_STATUS="unchanged"
      if [ "${DOTF_CFG_EMIT_RESULT:-0}" = "1" ]; then
        # shellcheck source=/dev/null
        source "${_DOTF_CONFIG_SAFE_DIR}/result.sh"
        dotf_emit_result unchanged "symlink already correct"
      fi
      return 0
    fi
    if [ -e "$target" ]; then
      dotf_backup_to "$target" >/dev/null
      ln -s "$expected_link" "$target"
      reason="replaced wrong symlink"
    else
      rm "$target"
      ln -s "$expected_link" "$target"
      reason="replaced broken symlink"
    fi
    DOTF_CFG_STATUS="changed"
    if [ "${DOTF_CFG_EMIT_RESULT:-0}" = "1" ]; then
      # shellcheck source=/dev/null
      source "${_DOTF_CONFIG_SAFE_DIR}/result.sh"
      dotf_emit_result changed "$reason"
    fi
    return 0
  fi

  if [ -e "$target" ]; then
    dotf_backup_to "$target" >/dev/null
    reason="backed up and linked"
  else
    reason="created symlink"
  fi
  ln -s "$expected_link" "$target"
  # shellcheck disable=SC2034
  DOTF_CFG_STATUS="changed"
  if [ "${DOTF_CFG_EMIT_RESULT:-0}" = "1" ]; then
    # shellcheck source=/dev/null
    source "${_DOTF_CONFIG_SAFE_DIR}/result.sh"
    dotf_emit_result changed "$reason"
  fi
  return 0
}

# 将整目录软链换成真实目录（只删 link，不跟随删除仓库内容）。
dotf_ensure_real_dir() {
  local target="$1"
  target=$(dotf_expand_path "$target")
  dotf_ensure_parent "$target"
  dotf_safe_path_check "$DOTF_TARGET_ROOT" "$target" 1
  if [ -L "$target" ]; then
    rm "$target"
    mkdir -m 700 "$target"
    return 0
  fi
  if [ -d "$target" ]; then
    return 0
  fi
  if [ -e "$target" ]; then
    dotf_backup_to "$target" >/dev/null
  fi
  mkdir -m 700 "$target"
}

# 把仓库里误放的运行时迁到 home 真实目录；保持旧行为。
dotf_migrate_runtime() {
  local src="$1"
  local dest="$2"
  if [ ! -e "$src" ] && [ ! -L "$src" ]; then
    return 0
  fi
  dotf_ensure_parent "$dest"
  dotf_safe_path_check "$DOTF_TARGET_ROOT" "$dest" 1
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    rm -rf "$src"
    return 0
  fi
  mv "$src" "$dest"
}
