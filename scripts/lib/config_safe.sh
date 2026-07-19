#!/usr/bin/env bash
# 公共配置安全库：路径展开、父目录创建、备份、symlink 幂等保证。
# 依赖: HOME；可选 DOTFILES_ROOT（相对源路径时需要）
# 可选: 已 source result.sh 时可通过 DOTF_CFG_EMIT_RESULT=1 发出 RESULT 行

# 默认备份目录（可覆盖）
: "${DOTF_BACKUP_DIR:=${HOME}/.config/backups}"

# 展开 ~/ 与相对路径（不 resolve symlink）
# 用法: dotf_expand_path <path> → stdout
dotf_expand_path() {
  local p="$1"
  if [ -z "$p" ]; then
    printf '\n'
    return 0
  fi
  # 仅处理字面 ~/ 前缀（调用方应传入未展开的路径）
  if [ "$p" = "~" ]; then
    p="$HOME"
  elif [ "${p#"~/"}" != "$p" ]; then
    p="${HOME}/${p#"~/"}"
  fi
  printf '%s\n' "$p"
}

# 确保父目录存在
# 用法: dotf_ensure_parent <path>
dotf_ensure_parent() {
  local path="$1"
  local parent
  parent=$(dirname "$path")
  if [ -n "$parent" ] && [ "$parent" != "." ] && [ ! -d "$parent" ]; then
    mkdir -p "$parent"
  fi
}

# 生成不冲突的备份目标路径
# 用法: dotf_backup_dest <src> → stdout
dotf_backup_dest() {
  local src="$1"
  local base
  base=$(basename "$src")
  local ts
  ts=$(date +%s)
  local dest
  dest="${DOTF_BACKUP_DIR}/${base}-${ts}"
  local n=0
  while [ -e "$dest" ]; do
    n=$((n + 1))
    dest="${DOTF_BACKUP_DIR}/${base}-${ts}-${n}"
  done
  printf '%s\n' "$dest"
}

# 将路径移动到备份目录；打印备份位置
# 用法: dotf_backup_to <src> → stdout 备份路径；失败非零
dotf_backup_to() {
  local src="$1"
  local dest
  mkdir -p "$DOTF_BACKUP_DIR"
  dest=$(dotf_backup_dest "$src")
  mv "$src" "$dest"
  printf '%s\n' "$dest"
}

# 解析期望源的绝对路径（用于比较）
# 用法: dotf_resolve_source <source> → stdout
# source 为绝对路径，或相对 DOTFILES_ROOT 的仓库内路径
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
  # readlink -f 在 macOS 可能不可用
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

# 确保 target 为指向 source 的 symlink。
# 正确链接 → unchanged；否则安全替换 → changed。
# 设置 DOTF_CFG_STATUS；可选发出 RESULT（需 result.sh + DOTF_MODULE/ACTION）
# 用法: dotf_ensure_symlink <source> <target>
dotf_ensure_symlink() {
  local source="$1"
  local target="$2"
  local expected_link expected_abs current
  local status="changed"
  local reason=""

  target=$(dotf_expand_path "$target")
  case "$source" in
  /*) expected_link="$source" ;;
  *) expected_link="${DOTFILES_ROOT}/${source}" ;;
  esac
  expected_abs=$(dotf_resolve_source "$source")

  dotf_ensure_parent "$target"

  if [ -L "$target" ]; then
    current=$(dotf_readlink_target "$target")
    if [ "$current" = "$expected_abs" ] || [ "$current" = "$expected_link" ]; then
      status="unchanged"
      reason="symlink already correct"
      DOTF_CFG_STATUS="$status"
      if [ "${DOTF_CFG_EMIT_RESULT:-0}" = "1" ]; then
        # shellcheck source=/dev/null
        source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/result.sh"
        dotf_emit_result unchanged "$reason"
      fi
      return 0
    fi
    # 错误或 broken symlink
    if [ -e "$target" ]; then
      # 指向存在目标的错误链接：先备份（备份的是 symlink 本身）
      dotf_backup_to "$target" >/dev/null
      ln -s "$expected_link" "$target"
      reason="replaced wrong symlink"
    else
      # broken：直接覆盖
      ln -sf "$expected_link" "$target"
      reason="replaced broken symlink"
    fi
    DOTF_CFG_STATUS="changed"
    if [ "${DOTF_CFG_EMIT_RESULT:-0}" = "1" ]; then
      # shellcheck source=/dev/null
      source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/result.sh"
      dotf_emit_result changed "$reason"
    fi
    return 0
  fi

  # 普通文件或目录 → 备份后建链
  if [ -e "$target" ]; then
    dotf_backup_to "$target" >/dev/null
    reason="backed up and linked"
  else
    reason="created symlink"
  fi
  ln -s "$expected_link" "$target"
  DOTF_CFG_STATUS="changed"
  if [ "${DOTF_CFG_EMIT_RESULT:-0}" = "1" ]; then
    # shellcheck source=/dev/null
    source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/result.sh"
    dotf_emit_result changed "$reason"
  fi
  return 0
}
