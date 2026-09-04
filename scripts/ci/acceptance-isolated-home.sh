#!/usr/bin/env bash
# Cross-platform acceptance. Every runtime write is confined to one disposable HOME.
# Keep this script compatible with the macOS system Bash 3.2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASH_BIN="${BASH_BIN:-bash}"
if ! command -v "$BASH_BIN" >/dev/null 2>&1; then
  echo "error: bash executable not found: $BASH_BIN" >&2
  exit 1
fi
PYTHON_BIN="$(command -v python3)"
GIT_BIN="$(command -v git)"
REAL_HOME="${HOME:-}"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dotf-acceptance.XXXXXX")"
TMP_HOME="$TMP_ROOT/home"
cleanup() { rm -rf "$TMP_ROOT"; }
trap cleanup EXIT HUP INT TERM

export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/.config"
export XDG_STATE_HOME="$TMP_HOME/.local/state"
export XDG_CACHE_HOME="$TMP_HOME/.cache"
export PYTHONDONTWRITEBYTECODE=1
umask 077
case "$HOME" in
  ""|"$REAL_HOME"|"$ROOT"|"$ROOT"/*)
    echo "error: acceptance HOME is not isolated" >&2
    exit 1
    ;;
esac
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

# The research profile can render runtime credential references without values.
# Remove relevant inherited values so acceptance cannot persist a real credential.
unset ZHIPU_API_KEY Z_AI_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

snapshot_paths() {
  "$PYTHON_BIN" - "$@" <<'PY'
import hashlib
import os
import stat
import sys
from pathlib import Path

records = []


def visit(path: Path, label: str) -> None:
    try:
        item = path.lstat()
    except FileNotFoundError:
        records.append((label, "missing", 0, 0, 0, 0, ""))
        return
    kind = stat.S_IFMT(item.st_mode)
    payload = ""
    if stat.S_ISREG(item.st_mode):
        payload = hashlib.sha256(path.read_bytes()).hexdigest()
    elif stat.S_ISLNK(item.st_mode):
        payload = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    records.append((label, kind, stat.S_IMODE(item.st_mode), item.st_ino, item.st_mtime_ns, item.st_size, payload))
    if stat.S_ISDIR(item.st_mode):
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda value: value.name):
                visit(Path(entry.path), label + "/" + entry.name)


for index, raw in enumerate(sys.argv[1:]):
    visit(Path(raw), "root-" + str(index))
digest = hashlib.sha256(repr(records).encode("utf-8")).hexdigest()
print("entries=%d metadata=mode,inode,mtime,size,sha256 digest=%s" % (len(records), digest))
PY
}

repo_snapshot() {
  "$PYTHON_BIN" - "$ROOT" "$GIT_BIN" <<'PY'
import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
git = sys.argv[2]


def git_bytes(*args: str) -> bytes:
    return subprocess.run([git, *args], cwd=root, check=True, capture_output=True).stdout


for label, args in (
    ("status", ("status", "--porcelain=v1", "-z")),
    ("diff", ("diff", "--binary", "--no-ext-diff")),
    ("cached", ("diff", "--cached", "--binary", "--no-ext-diff")),
):
    print(label + "=" + hashlib.sha256(git_bytes(*args)).hexdigest())

content = hashlib.sha256(b"repository-content-v1\0")


def visit(path: Path, relative: str) -> None:
    item = path.lstat()
    content.update(os.fsencode(relative) + b"\0")
    content.update(str(stat.S_IFMT(item.st_mode)).encode("ascii") + b"\0")
    content.update(str(stat.S_IMODE(item.st_mode)).encode("ascii") + b"\0")
    if stat.S_ISREG(item.st_mode):
        content.update(path.read_bytes())
    elif stat.S_ISLNK(item.st_mode):
        content.update(os.fsencode(os.readlink(path)))
    content.update(b"\0")
    if stat.S_ISDIR(item.st_mode):
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda value: value.name):
                if relative == "." and entry.name == ".git":
                    continue
                child_relative = entry.name if relative == "." else relative + "/" + entry.name
                visit(Path(entry.path), child_relative)


visit(root, ".")
print("content=" + content.hexdigest())
PY
}

backup_count() {
  if [ ! -d "$XDG_STATE_HOME/dotf/backups" ]; then
    printf '0\n'
    return
  fi
  find "$XDG_STATE_HOME/dotf/backups" -mindepth 1 -print | wc -l | tr -d ' '
}

repo_before="$(repo_snapshot)"

printf '%s\n' "==> isolated CLI smoke ($BASH_BIN)"
"$BASH_BIN" "$ROOT/bin/dotf" -h >/dev/null
"$BASH_BIN" "$ROOT/bin/dotf" init --list >/dev/null

printf '%s\n' "==> legacy writable config-link migration"
mkdir -p "$HOME/.logseq"
ln -s "$ROOT/config/editors/nvim" "$XDG_CONFIG_HOME/nvim"
ln -s "$ROOT/config/tools/logseq/settings" "$HOME/.logseq/settings"
config_first="$TMP_ROOT/config-first.log"
"$BASH_BIN" "$ROOT/bin/dotf" nvim logseq -c --yes >"$config_first"
for target in "$XDG_CONFIG_HOME/nvim" "$HOME/.logseq/settings"; do
  if [ -L "$target" ] || [ ! -d "$target" ]; then
    echo "error: legacy writable directory link was not migrated: $target" >&2
    exit 1
  fi
done
if [ ! -f "$ROOT/config/editors/nvim/init.lua" ] || [ ! -d "$ROOT/config/tools/logseq/settings" ]; then
  echo "error: repository source changed during legacy-link migration" >&2
  exit 1
fi
mkdir -p "$XDG_CONFIG_HOME/nvim/session" "$HOME/.logseq/plugins"
printf 'runtime-only\n' >"$XDG_CONFIG_HOME/nvim/session/acceptance-runtime"
printf '{"state":"runtime-only"}\n' >"$HOME/.logseq/plugins/acceptance-runtime.json"

config_before="$TMP_ROOT/config-before.snapshot"
snapshot_paths \
  "$XDG_CONFIG_HOME/nvim" \
  "$HOME/.logseq" \
  "$XDG_STATE_HOME/dotf/config-manifest.json" \
  "$XDG_STATE_HOME/dotf/backups" >"$config_before"
config_backups_before="$(backup_count)"
config_second="$TMP_ROOT/config-second.log"
"$BASH_BIN" "$ROOT/bin/dotf" nvim logseq -c --yes >"$config_second"
config_after="$TMP_ROOT/config-after.snapshot"
snapshot_paths \
  "$XDG_CONFIG_HOME/nvim" \
  "$HOME/.logseq" \
  "$XDG_STATE_HOME/dotf/config-manifest.json" \
  "$XDG_STATE_HOME/dotf/backups" >"$config_after"
if ! cmp -s "$config_before" "$config_after"; then
  echo "error: second config run rewrote a target, manifest, or backup" >&2
  exit 1
fi
if [ "$(backup_count)" != "$config_backups_before" ]; then
  echo "error: second config run created a backup" >&2
  exit 1
fi
case "$(cat "$config_second")" in
  *unchanged*) ;;
  *)
    echo "error: second config run did not report unchanged" >&2
    exit 1
    ;;
esac

printf '%s\n' "==> offline first-party Agent skills + MCP/environment sync"
STUB_BIN="$TMP_ROOT/offline-bin"
NETWORK_ATTEMPTED="$TMP_ROOT/network-attempted"
mkdir -p "$STUB_BIN"
for command_name in git curl wget npm npx; do
  cat >"$STUB_BIN/$command_name" <<EOF
#!/bin/sh
printf '%s\\n' '$command_name' >>'$NETWORK_ATTEMPTED'
echo 'error: network/acquisition is disabled during isolated acceptance' >&2
exit 97
EOF
  chmod 0700 "$STUB_BIN/$command_name"
done
export PATH="$STUB_BIN:$PATH"

agents_first="$TMP_ROOT/agents-first.log"
"$BASH_BIN" "$ROOT/scripts/agents/sync.sh" cursor --profile research >"$agents_first"
if ! grep -Eq 'done skills: changed=[1-9][0-9]* ' "$agents_first"; then
  echo "error: first Agent skills sync did not report changed" >&2
  exit 1
fi
if ! grep -q 'agents:mcp:cursor: changed' "$agents_first"; then
  echo "error: first MCP/environment sync did not report changed" >&2
  exit 1
fi
if [ -e "$NETWORK_ATTEMPTED" ]; then
  echo "error: first Agent sync attempted network/acquisition" >&2
  exit 1
fi

agents_before="$TMP_ROOT/agents-before.snapshot"
snapshot_paths "$HOME" >"$agents_before"
agents_backups_before="$(backup_count)"
agents_second="$TMP_ROOT/agents-second.log"
"$BASH_BIN" "$ROOT/scripts/agents/sync.sh" cursor --profile research >"$agents_second"
if ! grep -Eq 'done skills: changed=0 pruned=0 unchanged=[1-9][0-9]*' "$agents_second"; then
  echo "error: second Agent skills sync was not fully unchanged" >&2
  exit 1
fi
if ! grep -q 'agents:mcp:cursor: unchanged' "$agents_second"; then
  echo "error: second MCP/environment sync did not report unchanged" >&2
  exit 1
fi
if grep -Eq 'agents:mcp:[^:]+: changed' "$agents_second"; then
  echo "error: second MCP/environment sync reported a changed target" >&2
  exit 1
fi
if [ -e "$NETWORK_ATTEMPTED" ]; then
  echo "error: second Agent sync attempted network/acquisition" >&2
  exit 1
fi
agents_after="$TMP_ROOT/agents-after.snapshot"
snapshot_paths "$HOME" >"$agents_after"
if ! cmp -s "$agents_before" "$agents_after"; then
  echo "error: second Agent sync rewrote HOME targets/manifests or created state" >&2
  exit 1
fi
if [ "$(backup_count)" != "$agents_backups_before" ]; then
  echo "error: second Agent sync created a backup" >&2
  exit 1
fi

repo_after="$(repo_snapshot)"
if [ "$repo_after" != "$repo_before" ]; then
  echo "error: acceptance changed repository status, diff, or content" >&2
  diff_file="$TMP_ROOT/repository-snapshot.diff"
  printf '%s\n' "$repo_before" >"$TMP_ROOT/repository-before"
  printf '%s\n' "$repo_after" >"$TMP_ROOT/repository-after"
  diff -u "$TMP_ROOT/repository-before" "$TMP_ROOT/repository-after" >"$diff_file" || true
  cat "$diff_file" >&2
  exit 1
fi

printf '%s\n' "acceptance evidence: HOME=isolated cli=pass legacy_links=migrated writable_config=changed_then_unchanged agents_first=changed agents_second=unchanged metadata=inode+mtime+hash-stable backups=stable offline=stubbed secrets=none repo_status=unchanged repo_diff=unchanged repo_content=unchanged"
