#!/usr/bin/env bash
# Registry-driven configuration compatibility CLI (Bash 3.2+).
# All copy/merge/render writes are owned by dotf_core.config_handler.
set -e

DOTFILES_ROOT="${DOTFILES_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export DOTFILES_ROOT

# shellcheck source=/dev/null
source "$DOTFILES_ROOT/scripts/modules.sh"

get_config_def() {
  local name="$1" source target
  modules_exists "$name" || return 1
  modules_has "$name" config || return 1
  source=$(modules_source "$name") || return 1
  target=$(modules_target "$name") || return 1
  printf '%s:%s\n' "$source" "$target"
}

get_config_desc() {
  modules_desc "$1" 2>/dev/null || echo "$1"
}

get_all_config_names() {
  if [ "${1:-}" = "--filter-os" ]; then
    _modules_py names --capability config --filter-os
  else
    modules_names config
  fi
}

install_config() {
  local name="$1" pythonpath_value status run_id
  local -a state_args=()
  modules_has "$name" config || {
    echo "未知配置: $name" >&2
    return 1
  }
  pythonpath_value="${_DOTF_CORE_PYTHONPATH}"
  if [ -n "${PYTHONPATH:-}" ]; then
    pythonpath_value="${pythonpath_value}:${PYTHONPATH}"
  fi
  if [ -n "${XDG_STATE_HOME:-}" ]; then
    state_args=(--state-home "$XDG_STATE_HOME")
  fi
  run_id="${DOTF_RUN_ID:-legacy-$(date +%s)-$$}"
  status=$(PYTHONPATH="$pythonpath_value" \
    python3 -m dotf_core.config_handler "$name" \
    --repo-root "$DOTFILES_ROOT" --home "$HOME" \
    "${state_args[@]}" --run-id "$run_id") || return 1
  printf '%s: %s\n' "$name" "$status"
}

# Compatibility functions retained for old callers. They perform no direct cp,
# symlink, mkdir-to-managed-target, or ad-hoc serialization.
install_zsh() { install_config zsh; }
install_agents() { install_config agents; }
install_codex() { install_config codex; }
install_tmux() { install_config tmux; }
install_cursor() { install_config cursor; }
install_kiro_config() { install_config kiro; }
install_zcode_config() { install_config zcode; }
install_ocr_config() { install_config ocr; }
install_opencode_config() { install_config opencode; }
install_opencode() { install_config opencode; }
install_kimi_code_config() { install_config kimi-code; }
install_pi_config() { install_config pi; }

# Agent sync is intentionally separate from config deployment until its own
# plan/manifest transaction work is complete.
sync_agents() {
  "$DOTFILES_ROOT/scripts/agents/sync.sh" "$@"
}

install_all() {
  # shellcheck source=/dev/null
  source "$DOTFILES_ROOT/scripts/lib/runner.sh"
  local name
  for name in $(get_all_config_names --filter-os); do
    runner_run_action config "$name" || return 1
  done
}

main() {
  local config="${1:-}"
  if [ -z "$config" ]; then
    echo "用法: $0 <配置名|--all>"
    return 1
  fi
  case "$config" in
  --list)
    get_all_config_names
    ;;
  --list-desc)
    local name
    for name in $(get_all_config_names); do
      printf '%s\t%s\n' "$name" "$(get_config_desc "$name")"
    done
    ;;
  --all | -a)
    install_all
    ;;
  *)
    install_config "$config"
    ;;
  esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
