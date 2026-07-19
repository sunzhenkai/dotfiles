#!/usr/bin/env bash
# 统一 agents sync：skills/commands + MCP/env。
# 用法:
#   sync.sh [claude|cursor|opencode|codex|kimi-code|all]
#           [--skills-only|--env-only] [--profile NAME] [--dry-run] [--strict]
# 诊断请用: dotf agents -d  或  python3 scripts/agents/doctor.py
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
    echo "error: --doctor 已不再作为 sync 旁路旗标" >&2
    echo "请改用: dotf agents -d  或  dotf agents -cd" >&2
    exit 1
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
  python3 "$SCRIPT_DIR/env_sync.py" "${env_args[@]}"
fi

# --strict 保留：供将来 sync 自身严格模式使用（不再绑定 doctor）
if [ "$STRICT" -eq 1 ]; then
  :
fi

echo "✓ agents sync 完成"
