#!/bin/bash
# Claude Code / Desktop：settings、.mcp.json、合并 MCP 到 ~/.claude.json。
# 由 install-config.sh source，也可直接执行（会自行设置 DOTFILES_ROOT）。

install_claude() {
  local claude_dir="$HOME/.claude"
  if [ ! -d "$claude_dir" ]; then
    mkdir -p "$claude_dir"
  fi

  if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  Warning: ZHIPU_API_KEY environment variable is not set"
    echo "Please set it in your ~/.envrc or shell config before running the install script"
  fi

  local settings_target="$claude_dir/settings.json"
  local settings_template="$DOTFILES_ROOT/claude/settings.json"

  if [ -e "$settings_target" ]; then
    mv "$settings_target" "$settings_target-$TIMESTAMP"
  fi

  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$settings_template" >"$settings_target"
    echo "Installed: settings.json (with ZHIPU_API_KEY)"
  else
    cp "$settings_template" "$settings_target"
    echo "Installed: settings.json (please update ANTHROPIC_AUTH_TOKEN manually)"
  fi

  local claude_json_target="$HOME/.claude.json"
  local claude_json_source="$DOTFILES_ROOT/claude/.claude.json"

  if [ ! -f "$claude_json_source" ]; then
    echo "⚠️  Skipping ~/.claude.json symlink: no $claude_json_source in dotfiles"
  elif [ -L "$claude_json_target" ]; then
    local current_link
    current_link=$(readlink -f "$claude_json_target" 2>/dev/null || readlink "$claude_json_target")
    local expected_abs
    expected_abs=$(readlink -f "$claude_json_source" 2>/dev/null || echo "$claude_json_source")
    if [ "$current_link" = "$expected_abs" ]; then
      echo "Already installed: .claude.json"
    else
      [ -e "$claude_json_target" ] && mv "$claude_json_target" "$claude_json_target-$TIMESTAMP"
      ln -s "$claude_json_source" "$claude_json_target"
      echo "Installed: .claude.json"
    fi
  else
    [ -e "$claude_json_target" ] && mv "$claude_json_target" "$claude_json_target-$TIMESTAMP"
    ln -s "$claude_json_source" "$claude_json_target"
    echo "Installed: .claude.json"
  fi

  local mcp_target="$claude_dir/.mcp.json"
  local mcp_template="$DOTFILES_ROOT/claude/.mcp.json"

  if [ -e "$mcp_target" ]; then
    mv "$mcp_target" "$mcp_target-$TIMESTAMP"
  fi

  if [ -n "$ZHIPU_API_KEY" ]; then
    sed "s|\${ZHIPU_API_KEY}|$ZHIPU_API_KEY|g" "$mcp_template" >"$mcp_target"
    echo "Installed: .mcp.json (with ZHIPU_API_KEY)"
  else
    cp "$mcp_template" "$mcp_target"
    echo "Installed: .mcp.json (please update Authorization header manually)"
  fi

  local claude_state="$HOME/.claude.json"
  if [ -L "$claude_state" ] && [ ! -e "$claude_state" ]; then
    echo "⚠️  Warning: ~/.claude.json is a broken symlink; fix it before MCP merge can run"
  else
    python3 - "$mcp_target" "$claude_state" <<'PY'
import json, os, sys, tempfile
from pathlib import Path

mcp_path = Path(sys.argv[1])
dest = Path(os.path.expanduser(sys.argv[2]))
incoming = json.loads(mcp_path.read_text(encoding="utf-8"))["mcpServers"]
if dest.exists():
    data = json.loads(dest.read_text(encoding="utf-8"))
else:
    data = {}
data.setdefault("mcpServers", {})
data["mcpServers"].update(incoming)
text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
dest.parent.mkdir(parents=True, exist_ok=True)
fd, tmp = tempfile.mkstemp(
    dir=str(dest.parent), prefix=".claude.json.", suffix=".tmp", text=True
)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, dest)
except Exception:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise
PY
    echo "Merged MCP servers into ~/.claude.json (Claude Code user scope)"
  fi

  if [ -n "${SUDO_USER:-}" ] && [ "$(id -u)" -eq 0 ]; then
    chown -R "$SUDO_USER:" "$claude_dir" 2>/dev/null || true
    chown "$SUDO_USER:" "$claude_state" 2>/dev/null || true
    echo "Adjusted ownership for \$SUDO_USER on ~/.claude and ~/.claude.json"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -e
  DOTFILES_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  TIMESTAMP=$(date +%s)
  install_claude
fi
