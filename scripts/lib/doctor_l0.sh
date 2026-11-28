#!/usr/bin/env bash
# 公共 L0 doctor：binary / config target / symlink
# 输出行: pass|warn|fail|skip <scope>: <message>
# 返回: 0=无 fail，1=有 fail
# 依赖: lib/registry.sh；可选 config_safe.sh 的 expand

if ! type dotf_resolve_bin >/dev/null 2>&1; then
  # shellcheck source=/dev/null
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bin_resolve.sh"
fi

# 样式与 run_plan/progress 共用同一套常量。handler 输出会被捕获再转发，
# 这里不能用 [ -t 2 ] 判断，改看 run_plan.sh 推导好的 DOTF_COLOR。
DOTF_D0_OK=""; DOTF_D0_ERR=""; DOTF_D0_WARN=""; DOTF_D0_DIM=""; DOTF_D0_RST=""; DOTF_D0_BOLD=""
if [ "${DOTF_COLOR:-}" = "always" ]; then
  if eval "$(PYTHONPATH="${DOTFILES_ROOT:-.}/src${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m dotf_core.term --shell --tty 1 2>/dev/null)"; then
    DOTF_D0_OK="${DOTF_C_OK:-}"; DOTF_D0_ERR="${DOTF_C_ERR:-}"; DOTF_D0_WARN="${DOTF_C_WARN:-}"
    DOTF_D0_DIM="${DOTF_C_DIM:-}"; DOTF_D0_RST="${DOTF_C_RESET:-}"; DOTF_D0_BOLD="${DOTF_C_BOLD:-}"
  fi
fi

# 状态词保持在行首（颜色码在它前面），dotf_doctor_map_status 会先剥离 ANSI 再匹配。
dotf_doctor_line() {
  local status="$1"
  local color="$DOTF_D0_DIM"
  shift
  case "$status" in
  pass) color="$DOTF_D0_OK" ;;
  fail) color="$DOTF_D0_ERR" ;;
  warn) color="$DOTF_D0_WARN" ;;
  esac
  printf '%s%s%s  %s\n' "$color" "$status" "$DOTF_D0_RST" "$*"
}

dotf_doctor_tip() {
  printf '      %s建议: %s%s\n' "$DOTF_D0_DIM" "$*" "$DOTF_D0_RST"
}

dotf_doctor_l0() {
  local mod="$1"
  local failed=0
  local target bin_name cmd resolved raw

  printf '%s%sdoctor (%s) — L0%s\n' "$DOTF_D0_BOLD" "$DOTF_D0_DIM" "$mod" "$DOTF_D0_RST"

  if [ "$mod" = "agents" ]; then
    if ! python3 "$DOTFILES_ROOT/src/agents/managed_status.py"; then
      failed=1
    fi
  elif modules_has "$mod" config; then
    target="$(modules_target "$mod")"
    if [ -z "$target" ]; then
      dotf_doctor_line skip "config: 无 target 字段"
    else
      if type dotf_expand_path >/dev/null 2>&1; then
        target=$(dotf_expand_path "$target")
      else
        target="${target/#\~/$HOME}"
      fi
      if [ -e "$target" ] || [ -L "$target" ]; then
        if [ -L "$target" ] && [ ! -e "$target" ]; then
          dotf_doctor_line fail "config: 目标为损坏的 symlink → $target"
          dotf_doctor_tip "dotf $mod -c"
          failed=1
        else
          dotf_doctor_line pass "config: 目标存在 → $target"
        fi
      else
        dotf_doctor_line fail "config: 目标不存在 → $target"
        dotf_doctor_tip "dotf $mod -c"
        failed=1
      fi
    fi
  fi

  if modules_has "$mod" install; then
    bin_name="$(modules_bin "$mod")"
    if [ -n "$bin_name" ]; then
      if resolved="$(dotf_resolve_bin "$bin_name")"; then
        dotf_doctor_line pass "install: PATH 中找到 '$bin_name' ($resolved)"
      else
        raw="$(command -v "$bin_name" 2>/dev/null || true)"
        if [ -n "$raw" ] && dotf_is_mise_shim "$raw"; then
          dotf_doctor_line fail "install: '$bin_name' 命中失效 mise shim ($raw)，当前激活版本未提供该命令"
        elif [ -n "$raw" ]; then
          dotf_doctor_line fail "install: '$bin_name' 不可执行或为悬空链接 ($raw)"
        else
          dotf_doctor_line fail "install: PATH 中未找到 '$bin_name'"
        fi
        dotf_doctor_tip "dotf $mod -i"
        failed=1
      fi
    else
      cmd="$mod"
      if resolved="$(dotf_resolve_bin "$cmd")"; then
        dotf_doctor_line pass "install: PATH 中找到 '$cmd' ($resolved)"
      else
        dotf_doctor_line skip "install: 未声明 bin，且无法判定命令名（尝试过 '$cmd'）"
      fi
    fi
  fi

  if [ "$failed" -eq 0 ]; then
    printf '%s✓%s doctor (%s) L0 通过\n' "$DOTF_D0_OK" "$DOTF_D0_RST" "$mod"
  else
    printf '%s✗%s doctor (%s) L0 失败\n' "$DOTF_D0_ERR" "$DOTF_D0_RST" "$mod"
  fi
  return "$failed"
}

# 将 doctor 检查行映射为统一动作状态
# 用法: dotf_doctor_map_status <capture_file> → 设置 DOTF_DOCTOR_STATUS / DOTF_DOCTOR_REASON
dotf_doctor_map_status() {
  local file="$1"
  local has_fail=0 has_warn=0 has_pass=0 has_skip=0
  # 状态行可能带颜色码（DOTF_COLOR=always），先剥离再按行首状态词匹配。
  local plain
  plain="$(sed $'s/\033\\[[0-9;]*m//g' "$file" 2>/dev/null || true)"

  if grep -qE '^fail[[:space:]]' <<<"$plain"; then
    has_fail=1
  fi
  if grep -qE '^warn[[:space:]]' <<<"$plain"; then
    has_warn=1
  fi
  if grep -qE '^pass[[:space:]]' <<<"$plain"; then
    has_pass=1
  fi
  if grep -qE '^skip[[:space:]]' <<<"$plain"; then
    has_skip=1
  fi

  if [ "$has_fail" -eq 1 ]; then
    DOTF_DOCTOR_STATUS="failed"
    DOTF_DOCTOR_REASON="doctor reported fail"
    return 1
  fi
  if [ "$has_pass" -eq 1 ] && [ "$has_warn" -eq 0 ] && [ "$has_skip" -eq 0 ]; then
    DOTF_DOCTOR_STATUS="unchanged"
    DOTF_DOCTOR_REASON="doctor all pass"
    return 0
  fi
  if [ "$has_skip" -eq 1 ] && [ "$has_pass" -eq 0 ] && [ "$has_warn" -eq 0 ]; then
    # shellcheck disable=SC2034 # 跨脚本 setter：被 doctor_run.sh 与外部调用方读取
    DOTF_DOCTOR_STATUS="skipped"
    # shellcheck disable=SC2034 # 同上
    DOTF_DOCTOR_REASON="doctor skipped"
    return 0
  fi
  # shellcheck disable=SC2034 # 同上
  DOTF_DOCTOR_STATUS="unchanged"
  # shellcheck disable=SC2034 # 同上
  DOTF_DOCTOR_REASON="doctor pass/warn/skip"
  return 0
}
