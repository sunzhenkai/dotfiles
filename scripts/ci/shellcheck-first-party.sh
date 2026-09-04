#!/usr/bin/env bash
# Shellcheck every Git-tracked first-party shell entry; report explicit vendor exclusions.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v shellcheck >/dev/null 2>&1; then
  echo "error: shellcheck is required (no silent skip)" >&2
  exit 127
fi

selected="$(mktemp)"
excluded="$(mktemp)"
cleanup() { rm -f "$selected" "$excluded"; }
trap cleanup EXIT
selected_count=0
excluded_count=0

while IFS= read -r -d '' path; do
  case "$path" in
    config/multiplexers/tmux/3rd/*|agents/skills/pretty-view-ppt/references/html-ppt/*)
      printf '%s\n' "$path" >>"$excluded"
      excluded_count=$((excluded_count + 1))
      ;;
    *)
      printf '%s\0' "$path" >>"$selected"
      selected_count=$((selected_count + 1))
      ;;
  esac
done < <(git ls-files -z -- '*.sh' 'bin/dotf')

if [ "$selected_count" -eq 0 ]; then
  echo "error: tracked first-party shell inventory is empty" >&2
  exit 1
fi

echo "shellcheck inventory: selected=$selected_count excluded_third_party=$excluded_count"
if [ "$excluded_count" -gt 0 ]; then
  echo "explicit third-party exclusions:"
  sed 's/^/  - /' "$excluded"
fi
xargs -0 shellcheck -x --severity=warning -- <"$selected"
