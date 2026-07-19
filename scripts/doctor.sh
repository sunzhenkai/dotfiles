#!/usr/bin/env bash
# 统一 doctor 入口：委托 L0 + 可选 L1
# 用法: doctor.sh <module> [--deep] [extra...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOTFILES_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export DOTFILES_ROOT

# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/modules.sh"
# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/lib/doctor_run.sh"

main() {
  local mod="${1:-}"
  if [ -z "$mod" ]; then
    echo "用法: $0 <module> [--deep] [agents doctor 选项...]"
    exit 1
  fi
  shift

  if ! modules_exists "$mod"; then
    echo "错误: 未知模块 '$mod'"
    echo "可用模块:"
    modules_list | sed 's/^/  /'
    exit 1
  fi

  if ! modules_has "$mod" doctor; then
    echo "错误: 模块 '$mod' 无诊断步骤"
    exit 1
  fi

  # OS 不适用时 skip（零退出）
  local os_line os_list current
  os_line="$(modules_get "$mod" | grep '^os=' || true)"
  if [ -n "$os_line" ]; then
    os_list="${os_line#os=}"
    current="$(modules_detect_os)"
    local ok=0 part
    IFS=',' read -ra parts <<<"$os_list"
    for part in "${parts[@]}"; do
      if [ "$part" = "$current" ]; then
        ok=1
        break
      fi
      if [ "$part" = "linux" ] && [ "$current" != "darwin" ] && [ "$current" != "unknown" ]; then
        ok=1
        break
      fi
    done
    if [ "$ok" -eq 0 ]; then
      echo "skip  doctor ($mod): 当前 OS ($current) 不适用 (os=$os_list)"
      export DOTF_MODULE="$mod" DOTF_ACTION=doctor
      # shellcheck source=/dev/null
      source "$DOTFILES_ROOT/scripts/lib/result.sh"
      dotf_emit_result skipped "os not applicable"
      exit 0
    fi
  fi

  if ! dotf_doctor_run "$mod" "$@"; then
    exit 1
  fi
}

main "$@"
