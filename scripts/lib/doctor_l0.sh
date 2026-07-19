#!/usr/bin/env bash
# 公共 L0 doctor：binary / config target / symlink
# 输出行: pass|warn|fail|skip <scope>: <message>
# 返回: 0=无 fail，1=有 fail
# 依赖: modules.sh；可选 config_safe.sh 的 expand

dotf_doctor_l0() {
  local mod="$1"
  local failed=0
  local target bin_name cmd

  echo "doctor ($mod) — L0"

  if modules_has "$mod" config; then
    target="$(modules_target "$mod")"
    if [ -z "$target" ]; then
      echo "skip  config: 无 target 字段"
    else
      if type dotf_expand_path >/dev/null 2>&1; then
        target=$(dotf_expand_path "$target")
      else
        target="${target/#\~/$HOME}"
      fi
      if [ -e "$target" ] || [ -L "$target" ]; then
        if [ -L "$target" ] && [ ! -e "$target" ]; then
          echo "fail  config: 目标为损坏的 symlink → $target"
          echo "      建议: dotf $mod -c"
          failed=1
        else
          echo "pass  config: 目标存在 → $target"
        fi
      else
        echo "fail  config: 目标不存在 → $target"
        echo "      建议: dotf $mod -c"
        failed=1
      fi
    fi
  fi

  if modules_has "$mod" install; then
    bin_name="$(modules_bin "$mod")"
    if [ -n "$bin_name" ]; then
      if command -v "$bin_name" >/dev/null 2>&1; then
        echo "pass  install: PATH 中找到 '$bin_name' ($(command -v "$bin_name"))"
      else
        echo "fail  install: PATH 中未找到 '$bin_name'"
        echo "      建议: dotf $mod -i"
        failed=1
      fi
    else
      cmd="$mod"
      if [ "$cmd" = "codebuddy-code" ]; then
        cmd="codebuddy"
      fi
      if command -v "$cmd" >/dev/null 2>&1; then
        echo "pass  install: PATH 中找到 '$cmd' ($(command -v "$cmd"))"
      else
        echo "skip  install: 未声明 bin，且无法判定命令名（尝试过 '$cmd'）"
      fi
    fi
  fi

  if [ "$failed" -eq 0 ]; then
    echo "✓ doctor ($mod) L0 通过"
  else
    echo "✗ doctor ($mod) L0 失败"
  fi
  return "$failed"
}

# 将 doctor 检查行映射为统一动作状态
# 用法: dotf_doctor_map_status <capture_file> → 设置 DOTF_DOCTOR_STATUS / DOTF_DOCTOR_REASON
dotf_doctor_map_status() {
  local file="$1"
  local has_fail=0 has_warn=0 has_pass=0 has_skip=0

  if grep -qE '^fail[[:space:]]' "$file" 2>/dev/null; then
    has_fail=1
  fi
  if grep -qE '^warn[[:space:]]' "$file" 2>/dev/null; then
    has_warn=1
  fi
  if grep -qE '^pass[[:space:]]' "$file" 2>/dev/null; then
    has_pass=1
  fi
  if grep -qE '^skip[[:space:]]' "$file" 2>/dev/null; then
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
    DOTF_DOCTOR_STATUS="skipped"
    DOTF_DOCTOR_REASON="doctor skipped"
    return 0
  fi
  DOTF_DOCTOR_STATUS="unchanged"
  DOTF_DOCTOR_REASON="doctor pass/warn/skip"
  return 0
}
