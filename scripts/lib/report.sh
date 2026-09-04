#!/usr/bin/env bash
# Strict latest-run summary access. Persistence is owned by execution_state.py.

# shellcheck disable=SC2034  # public constant for sourced compatibility callers
REPORT_SCHEMA_VERSION=1

_dotf_report_root() {
  if [ -n "${DOTFILES_ROOT:-}" ]; then
    printf '%s\n' "$DOTFILES_ROOT"
  else
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
  fi
}

dotf_state_dir() {
  local base="${XDG_STATE_HOME:-$HOME/.local/state}"
  printf '%s\n' "${base}/dotf"
}

dotf_report_path() {
  printf '%s\n' "$(dotf_state_dir)/last-run.json"
}

dotf_report_load() {
  local root path
  root="$(_dotf_report_root)"
  path="$(dotf_report_path)"
  python3 "$root/scripts/execution_state.py" load-latest --path "$path"
}
