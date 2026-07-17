#!/usr/bin/env bash
# 统一 agents sync：skills/commands + MCP/env。
# 用法:
#   sync.sh [claude|cursor|opencode|codex|kimi-code|all]
#           [--skills-only|--env-only] [--profile NAME] [--dry-run] [--doctor] [--strict]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 是 agents sync 所必需的" >&2
  exit 1
fi

TOOL="all"
SKILLS=1
ENV=1
PROFILE=""
DRY_RUN=0
DOCTOR=0
STRICT=0
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
  claude | cursor | opencode | codex | kimi-code | all)
    TOOL="$1"
    ;;
  --skills-only)
    SKILLS=1
    ENV=0
    ;;
  --env-only)
    SKILLS=0
    ENV=1
    ;;
  --profile)
    shift
    PROFILE="${1:-}"
    if [ -z "$PROFILE" ]; then
      echo "error: --profile 需要参数" >&2
      exit 1
    fi
    ;;
  --dry-run)
    DRY_RUN=1
    EXTRA+=(--dry-run)
    ;;
  --doctor)
    DOCTOR=1
    ;;
  --strict)
    STRICT=1
    ;;
  --root)
    shift
    ROOT="${1:-}"
    ;;
  -h | --help)
    sed -n '2,7p' "$0" | sed 's/^# //'
    exit 0
    ;;
  *)
    echo "error: 未知参数 '$1'" >&2
    exit 1
    ;;
  esac
  shift
done

echo "agents sync  tool=$TOOL  skills=$SKILLS  env=$ENV  profile=${PROFILE:-default}  dry_run=$DRY_RUN"

if [ "$SKILLS" -eq 1 ]; then
  echo "--- skills/commands ---"
  skills_args=(--root "$ROOT" "$TOOL")
  if [ "$DRY_RUN" -eq 1 ]; then
    skills_args+=(--dry-run)
  fi
  python3 "$SCRIPT_DIR/sync.py" "${skills_args[@]}"
fi

if [ "$ENV" -eq 1 ]; then
  echo "--- mcp/env ---"
  env_args=(--root "$ROOT" "$TOOL")
  if [ -n "$PROFILE" ]; then
    env_args+=(--profile "$PROFILE")
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    env_args+=(--dry-run)
  fi
  python3 "$ROOT/scripts/agent-env/sync.py" "${env_args[@]}"
fi

if [ "$DOCTOR" -eq 1 ]; then
  echo "--- doctor ---"
  doctor_args=(--root "$ROOT")
  if [ -n "$PROFILE" ]; then
    doctor_args+=(--profile "$PROFILE")
  fi
  if [ "$TOOL" != "all" ]; then
    doctor_args+=(--tool "$TOOL")
  fi
  set +e
  python3 "$SCRIPT_DIR/doctor.py" "${doctor_args[@]}"
  doc_rc=$?
  set -e
  if [ "$STRICT" -eq 1 ] && [ "$doc_rc" -ne 0 ]; then
    exit "$doc_rc"
  fi
  if [ "$doc_rc" -ne 0 ]; then
    echo "⚠️  doctor 发现 fail（非 --strict，不阻断 sync）"
  fi
fi

echo "✓ agents sync 完成"
