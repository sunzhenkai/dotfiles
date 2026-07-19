#!/usr/bin/env bash
# 统一动作 runner：约定式处理器发现、lazy load、结果规范化与失败传播。
# 由 run_plan.sh source；也可单独测试。
#
# 环境覆盖:
#   DOTF_HANDLERS_DIR  处理器根目录（默认 $DOTFILES_ROOT/scripts/modules）
#   DOTF_REQUIRE_HANDLERS=1  缺少约定式处理器时失败（不走 compat）
#   DOTF_LOAD_LOG      若设置，每次加载处理器时追加一行（测试用）

# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/result.sh"
# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/compat_adapter.sh"

runner_handlers_dir() {
  if [ -n "${DOTF_HANDLERS_DIR:-}" ]; then
    printf '%s\n' "$DOTF_HANDLERS_DIR"
  else
    printf '%s\n' "${DOTFILES_ROOT}/scripts/modules"
  fi
}

# 约定式处理器路径；存在则打印路径并以 0 返回
runner_handler_path() {
  local module="$1"
  local action="$2"
  local path
  path="$(runner_handlers_dir)/${module}/${action}.sh"
  if [ -f "$path" ]; then
    printf '%s\n' "$path"
    return 0
  fi
  return 1
}

# 记录 lazy load（仅当前动作处理器，不预加载其它模块）
runner_mark_loaded() {
  local module="$1"
  local action="$2"
  local path="$3"
  if [ -n "${DOTF_LOAD_LOG:-}" ]; then
    printf '%s\t%s\t%s\n' "$module" "$action" "$path" >>"$DOTF_LOAD_LOG"
  fi
}

# 解析处理器 stdout/stderr 中最后一条 RESULT 行
# 用法: runner_parse_result <capture_file> → 设置 _RS_* 变量
runner_parse_result() {
  local file="$1"
  _RS_STATUS=""
  _RS_MODULE=""
  _RS_ACTION=""
  _RS_DURATION=""
  _RS_EXIT=""
  _RS_REASON=""
  local line
  line=$(grep $'^RESULT\t' "$file" 2>/dev/null | tail -n 1 || true)
  if [ -z "$line" ]; then
    return 1
  fi
  IFS=$'\t' read -r _tag _RS_STATUS _RS_MODULE _RS_ACTION _RS_DURATION _RS_EXIT _RS_REASON <<<"$line"
  if ! dotf_result_is_valid "$_RS_STATUS"; then
    return 1
  fi
  return 0
}

runner_now_ms() {
  # 优先纳秒；不可用时退回秒精度
  local ns
  ns=$(date +%s%N 2>/dev/null || true)
  if [ -n "$ns" ] && [ "${#ns}" -gt 10 ]; then
    printf '%s\n' "$((ns / 1000000))"
  else
    printf '%s\n' "$(($(date +%s) * 1000))"
  fi
}

# 执行单个计划动作；打印人类可读行与 RESULT 行。
# 返回: 0=非 failed，非零=failed（传播处理器退出码）
# 用法: runner_run_action <action> <module> [extra...]
runner_run_action() {
  local action="$1"
  local module="$2"
  shift 2
  local -a extra=("$@")
  local handler=""
  local start_ms end_ms duration_ms
  local rc=0
  local capture
  local status reason exit_code

  export DOTF_MODULE="$module"
  export DOTF_ACTION="$action"

  start_ms=$(runner_now_ms)
  capture=$(mktemp)

  # doctor：始终走 L0 + 可选 L1（doctor.sh 表示 L1，不是独占入口）
  if [ "$action" = "doctor" ]; then
    if [ "${DOTF_DEEP:-0}" = "1" ]; then
      has_deep=0
      for a in ${extra[@]+"${extra[@]}"}; do
        [ "$a" = "--deep" ] && has_deep=1
      done
      if [ "$has_deep" -eq 0 ]; then
        extra+=(--deep)
      fi
    fi
    if [ -f "$(runner_handlers_dir)/${module}/doctor.sh" ]; then
      runner_mark_loaded "$module" "doctor" "$(runner_handlers_dir)/${module}/doctor.sh"
    fi
    (
      set -euo pipefail
      export DOTFILES_ROOT
      export DOTF_MODULE="$module"
      export DOTF_ACTION=doctor
      # shellcheck source=/dev/null
      source "$DOTFILES_ROOT/scripts/lib/doctor_run.sh"
      dotf_doctor_run "$module" ${extra[@]+"${extra[@]}"}
    ) >"$capture" 2>&1 || rc=$?
  elif handler=$(runner_handler_path "$module" "$action"); then
    runner_mark_loaded "$module" "$action" "$handler"
    # 约定式处理器：仅执行该脚本（lazy load；公共库由处理器自行 source）
    (
      set -euo pipefail
      export DOTFILES_ROOT
      export DOTF_MODULE="$module"
      export DOTF_ACTION="$action"
      # 预注入结果协议，处理器可直接调用 dotf_result_*
      # shellcheck source=/dev/null
      source "$DOTFILES_ROOT/scripts/lib/result.sh"
      # shellcheck source=/dev/null
      source "$handler" ${extra[@]+"${extra[@]}"}
    ) >"$capture" 2>&1 || rc=$?
  else
    if [ "${DOTF_REQUIRE_HANDLERS:-0}" = "1" ]; then
      end_ms=$(runner_now_ms)
      duration_ms=$((end_ms - start_ms))
      [ "$duration_ms" -lt 0 ] && duration_ms=0
      reason="缺少处理器 $(runner_handlers_dir)/${module}/${action}.sh"
      export DOTF_MODULE="$module" DOTF_ACTION="$action"
      dotf_emit_result failed "$reason" "$duration_ms" 1
      echo "✗ $action $module → failed (${duration_ms}ms) $reason" >&2
      rm -f "$capture"
      return 1
    fi
    # 迁移期：compat 适配器
    (
      export DOTFILES_ROOT
      export DOTF_MODULE="$module"
      export DOTF_ACTION="$action"
      compat_run_action "$action" "$module" "${extra[@]+"${extra[@]}"}"
    ) >"$capture" 2>&1 || rc=$?
  fi

  end_ms=$(runner_now_ms)
  duration_ms=$((end_ms - start_ms))
  [ "$duration_ms" -lt 0 ] && duration_ms=0

  # 将处理器日志透出（不含 RESULT 行，避免重复）
  if [ -s "$capture" ]; then
    grep -v $'^RESULT\t' "$capture" || true
  fi

  if runner_parse_result "$capture"; then
    status="$_RS_STATUS"
    reason="${_RS_REASON:-}"
    exit_code="${_RS_EXIT:-$rc}"
  else
    # 无 RESULT：按退出码映射
    if [ "$rc" -eq 0 ]; then
      status="changed"
      reason="ok"
      exit_code=0
    else
      status="failed"
      reason="exit $rc"
      exit_code="$rc"
    fi
  fi

  # 处理器声称成功但进程非零 → 强制 failed
  if [ "$rc" -ne 0 ] && [ "$status" != "failed" ]; then
    status="failed"
    reason="${reason:-handler exit $rc}"
    exit_code="$rc"
  fi
  # failed 必须非零退出码
  if [ "$status" = "failed" ] && [ "$exit_code" -eq 0 ]; then
    exit_code=1
  fi

  export DOTF_MODULE="$module" DOTF_ACTION="$action"
  # 最终规范化 RESULT（stdout，供汇总/报告）
  DOTF_RESULT_FILE="" dotf_emit_result "$status" "$reason" "$duration_ms" "$exit_code"

  case "$status" in
  failed)
    echo "✗ $action $module → failed (${duration_ms}ms) $reason" >&2
    rm -f "$capture"
    return "$exit_code"
    ;;
  *)
    echo "✓ $action $module → $status (${duration_ms}ms) $reason"
    rm -f "$capture"
    return 0
    ;;
  esac
}
