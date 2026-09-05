#!/usr/bin/env bash
# 统一 agents sync：一手 skills + 第三方默认 skill + OpenSpec CLI skills（~/.agents/skills 与 Kiro CLI）+ MCP/env（按 tool 过滤）。
# 用法:
#   sync.sh [<tool>|all]
#           [--skills-only|--env-only] [--profile NAME] [--dry-run] [--strict]
# 工具名称与能力由 agents/env/vendors.yaml 校验。
# 诊断请用: dotf agents -d  或  python3 scripts/agents/doctor.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 是 agents sync 所必需的" >&2
  exit 1
fi

TOOL="all"
TOOL_SET=0
SKILLS=1
ENV=1
PROFILE=""
DRY_RUN=0
STRICT=0

while [ $# -gt 0 ]; do
  case "$1" in
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
    if [ "$TOOL_SET" -eq 1 ]; then
      echo "error: 只能指定一个工具（额外参数: '$1'）" >&2
      exit 1
    fi
    TOOL="$1"
    TOOL_SET=1
    ;;
  esac
  shift
done

validation_args=("$TOOL" --root "$ROOT" --validate-tool)
if [ -n "$PROFILE" ]; then
  validation_args+=(--profile "$PROFILE")
fi
if [ "$ENV" -eq 1 ] && [ "$SKILLS" -eq 0 ] && [ "$TOOL" != "all" ]; then
  validation_args+=(--require-mcp)
fi
python3 "$SCRIPT_DIR/env_sync.py" "${validation_args[@]}"

echo "agents sync  tool=$TOOL  skills=$SKILLS  env=$ENV  profile=${PROFILE:-default}  dry_run=$DRY_RUN"

if [ "$SKILLS" -eq 1 ]; then
  echo "--- skills ---"
  # skills 同步到共享 ~/.agents/skills，并为 Kiro CLI 写 ~/.kiro/skills；
  # 与 tool 过滤无关，一次性执行
  skills_args=(--root "$ROOT")
  if [ "$DRY_RUN" -eq 1 ]; then
    skills_args+=(--dry-run)
  fi
  python3 "$SCRIPT_DIR/sync.py" "${skills_args[@]}"
  echo "--- default skills ---"
  python3 "$SCRIPT_DIR/defaults.py" "${skills_args[@]}"
  echo "--- openspec skills ---"
  python3 "$SCRIPT_DIR/openspec_skills.py" "${skills_args[@]}"
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
