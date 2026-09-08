#!/bin/bash
# macOS hosted-runner gate: system Bash 3.2 only; never substitute Homebrew Bash.
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "error: macOS smoke must run on Darwin" >&2
  exit 1
fi
if [ "${BASH_VERSINFO[0]}" -ne 3 ] || [ "${BASH_VERSINFO[1]}" -ne 2 ]; then
  echo "error: expected system Bash 3.2, got ${BASH_VERSION}" >&2
  exit 1
fi

PYTHON_BIN="$(command -v python3)"
PYTHON_BIN_DIR="$(dirname "$PYTHON_BIN")"
PATH="$PYTHON_BIN_DIR:/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"
export PATH
export PYTHON_BIN
hash -r
resolved_bash="$(command -v bash)"
case "$resolved_bash" in
  /bin/bash|/usr/bin/bash) ;;
  *)
    echo "error: PATH resolved non-system Bash: $resolved_bash" >&2
    exit 1
    ;;
esac

echo "macOS bash evidence: executable=/bin/bash version=${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASH_BIN=/bin/bash /bin/bash "$ROOT/scripts/ci/acceptance-isolated-home.sh"
