#!/usr/bin/env bash
# 模块动作结果协议（内部稳定行协议）
# 状态: changed | unchanged | skipped | failed
#
# 行格式（TAB 分隔）:
#   RESULT  <status>  <module>  <action>  <duration_ms>  <exit_code>  <reason>
#
# 处理器可调用:
#   dotf_result_changed "reason"
#   dotf_result_unchanged "reason"
#   dotf_result_skipped "reason"
#   dotf_result_failed "reason"   # 同时以非零退出（默认 1）
#
# 环境变量（由 runner 注入）:
#   DOTF_MODULE  DOTF_ACTION  DOTF_RESULT_FILE（可选，写入此文件而非 stdout）

dotf_result_is_valid() {
  case "$1" in
  changed | unchanged | skipped | failed) return 0 ;;
  *) return 1 ;;
  esac
}

# 发出一条 RESULT 行。duration_ms / exit_code 可由 runner 事后补全。
# 用法: dotf_emit_result <status> [reason] [duration_ms] [exit_code]
dotf_emit_result() {
  local status="$1"
  local reason="${2:-}"
  local duration_ms="${3:-0}"
  local exit_code="${4:-0}"
  local module="${DOTF_MODULE:-}"
  local action="${DOTF_ACTION:-}"
  local line

  if ! dotf_result_is_valid "$status"; then
    echo "dotf_emit_result: 非法状态 '$status'" >&2
    return 2
  fi

  # 原因中禁止 TAB/换行，保持行协议可解析
  reason="${reason//$'\t'/ }"
  reason="${reason//$'\n'/ }"

  line=$(printf 'RESULT\t%s\t%s\t%s\t%s\t%s\t%s' \
    "$status" "$module" "$action" "$duration_ms" "$exit_code" "$reason")

  if [ -n "${DOTF_RESULT_FILE:-}" ]; then
    printf '%s\n' "$line" >>"$DOTF_RESULT_FILE"
  else
    printf '%s\n' "$line"
  fi
}

dotf_result_changed() {
  dotf_emit_result changed "${1:-changed}"
}

dotf_result_unchanged() {
  dotf_emit_result unchanged "${1:-unchanged}"
}

dotf_result_skipped() {
  dotf_emit_result skipped "${1:-skipped}"
}

dotf_result_failed() {
  local reason="${1:-failed}"
  local code="${2:-1}"
  dotf_emit_result failed "$reason" 0 "$code"
  # 在 runner 子 shell 中结束进程，确保失败不被吞掉
  exit "$code"
}
