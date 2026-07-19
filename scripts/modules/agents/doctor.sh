#!/usr/bin/env bash
# agents L1：领域深度诊断（由 --deep 触发）
# 额外参数透传给 scripts/agents/doctor.py
set -euo pipefail
python3 "$DOTFILES_ROOT/scripts/agents/doctor.py" "$@"
