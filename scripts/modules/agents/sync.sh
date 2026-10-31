#!/usr/bin/env bash
# 统一 agents sync：一手 skills + 第三方默认 skill + OpenSpec CLI skills（~/.agents/skills 与 Kiro CLI）
# + 全局 AGENTS.md。
# 用法:
#   sync.sh [--dry-run] [--on-conflict=block|backup] [--takeover=skip|backup] [--verbose]
# 冲突默认「先备份再继续」：owned 漂移（内容/mode/identity）与 unowned 接管都会备份旧字节后覆写；
# --on-conflict=block / --takeover=skip 恢复严格模式（冲突即跳过）。不安全目标始终 fail closed。
# 工具过滤已移除：skills/instructions 与工具无关，一律全量执行。
# 诊断请用: dotf agents -d  或  PYTHONPATH=scripts python3 src/agents/doctor.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 单一 ROOT 锚点：管线内用 run_plan.sh 导出的 DOTFILES_ROOT，直调时回退自算
ROOT="${DOTFILES_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
_SRC_AGENTS="$ROOT/src/agents"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 是 agents sync 所必需的" >&2
  exit 1
fi

DRY_RUN=0
ON_CONFLICT=""
ON_TAKEOVER=""
VERBOSE=0

while [ $# -gt 0 ]; do
  case "$1" in
  --dry-run)
    DRY_RUN=1
    ;;
  --doctor)
    echo "error: --doctor 已不再作为 sync 旁路旗标" >&2
    echo "请改用: dotf agents -d  或  dotf agents -cd" >&2
    exit 1
    ;;
  --verbose)
    VERBOSE=1
    ;;
  --on-conflict)
    shift
    ON_CONFLICT="${1:-}"
    if [ "$ON_CONFLICT" != "block" ] && [ "$ON_CONFLICT" != "backup" ]; then
      echo "error: --on-conflict 只接受 block 或 backup" >&2
      exit 1
    fi
    ;;
  --on-conflict=*)
    ON_CONFLICT="${1#--on-conflict=}"
    if [ "$ON_CONFLICT" != "block" ] && [ "$ON_CONFLICT" != "backup" ]; then
      echo "error: --on-conflict 只接受 block 或 backup" >&2
      exit 1
    fi
    ;;
  --takeover)
    shift
    ON_TAKEOVER="${1:-}"
    if [ "$ON_TAKEOVER" != "skip" ] && [ "$ON_TAKEOVER" != "backup" ]; then
      echo "error: --takeover 只接受 skip 或 backup" >&2
      exit 1
    fi
    ;;
  --takeover=*)
    ON_TAKEOVER="${1#--takeover=}"
    if [ "$ON_TAKEOVER" != "skip" ] && [ "$ON_TAKEOVER" != "backup" ]; then
      echo "error: --takeover 只接受 skip 或 backup" >&2
      exit 1
    fi
    ;;
  --root)
    shift
    ROOT="${1:-}"
    if [ -z "$ROOT" ]; then
      echo "error: --root 需要参数" >&2
      exit 1
    fi
    ;;
  -h | --help)
    sed -n '2,8p' "$0" | sed 's/^# //'
    exit 0
    ;;
  -*)
    echo "error: 未知参数 '$1'" >&2
    exit 1
    ;;
  *)
    # 兼容旧 `<tool>|all` 位置参数：忽略
    ;;
  esac
  shift
done

export PYTHONUNBUFFERED=1

echo "agents sync  dry_run=$DRY_RUN"

echo "--- instructions ---"
instructions_args=(--root "$ROOT")
if [ "$DRY_RUN" -eq 1 ]; then
  instructions_args+=(--dry-run)
fi
# 把 on-conflict / takeover 透传给 instructions 段，行为与 skill 段一致。
if [ -n "$ON_CONFLICT" ]; then
  instructions_args+=(--on-conflict "$ON_CONFLICT")
fi
if [ -n "$ON_TAKEOVER" ]; then
  instructions_args+=(--takeover "$ON_TAKEOVER")
fi
python3 "$_SRC_AGENTS/instructions.py" "${instructions_args[@]}"

skills_args=(--root "$ROOT")
if [ "$DRY_RUN" -eq 1 ]; then
  skills_args+=(--dry-run)
fi
if [ -n "$ON_CONFLICT" ]; then
  skills_args+=(--on-conflict "$ON_CONFLICT")
  export DOTF_ON_CONFLICT="$ON_CONFLICT"
fi
if [ -n "$ON_TAKEOVER" ]; then
  skills_args+=(--takeover "$ON_TAKEOVER")
  export DOTF_TAKEOVER="$ON_TAKEOVER"
fi
if [ "$VERBOSE" -eq 1 ]; then
  skills_args+=(--verbose)
  export DOTF_VERBOSE=1
fi

# 阶段互不阻塞：一手 / defaults / OpenSpec 各自记 rc，最后汇总并点名失败阶段。
sync_rc=0
failed_stages=()
failed_details=()

_run_sync_stage() {
  local stage="$1"
  local banner="$2"
  local step_rc log detail
  shift 2
  echo "$banner"
  log="$(mktemp "${TMPDIR:-/tmp}/dotf-sync-${stage}-XXXXXX.log")"
  set +e
  python3 "$@" 2>&1 | tee "$log"
  step_rc=${PIPESTATUS[0]}
  set -e
  if [ "$step_rc" -ne 0 ]; then
    detail="$(grep -m1 '^error:' "$log" 2>/dev/null || true)"
    echo "error: agents sync 阶段失败: $stage（exit=$step_rc）" >&2
    failed_stages+=("$stage")
    failed_details+=("${detail:-（无 error 行，见上方该阶段输出）}")
    sync_rc=$step_rc
  fi
  rm -f "$log"
}

_run_sync_stage skills "--- skills ---" "$_SRC_AGENTS/sync.py" "${skills_args[@]}"
_run_sync_stage defaults "--- default skills ---" "$_SRC_AGENTS/defaults.py" "${skills_args[@]}"
_run_sync_stage openspec "--- openspec skills ---" "$_SRC_AGENTS/openspec_skills.py" "${skills_args[@]}"

if [ "$sync_rc" -ne 0 ]; then
  joined=$(printf '%s, ' "${failed_stages[@]}")
  joined="${joined%, }"
  echo "error: agents sync 有阶段失败: ${joined}（exit=$sync_rc）" >&2
  for detail in "${failed_details[@]}"; do
    echo "  ↳ $detail" >&2
  done
  exit "$sync_rc"
fi

echo "✓ agents sync 完成"
