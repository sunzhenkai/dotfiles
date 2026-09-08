#!/usr/bin/env bash
# TUI smoke: isolated HOME；fake handlers 跑 install + doctor；断言 modules-state.yaml。
# 端到端覆盖 modules_state.run_plan.sh hook + state 文件；不修真实 HOME。
set -euo pipefail
LAUNCH_HOME="${HOME:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

TMP_HOME="$(mktemp -d)"
cleanup() { rm -rf "$TMP_HOME"; }
trap cleanup EXIT

export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/.config"
export XDG_STATE_HOME="$TMP_HOME/.local/state"
export XDG_CACHE_HOME="$TMP_HOME/.cache"

# textual lives in user site-packages; compute it from launch HOME so the
# smoke HOME override doesn't shadow the user site.
USER_SITE="$(HOME="$LAUNCH_HOME" python3 -c 'import site; print(site.getusersitepackages())')"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

# Fake handlers: install / doctor emit changed RESULT lines
HANDLERS="$TMP_HOME/handlers"
mkdir -p "$HANDLERS/demo/install" "$HANDLERS/demo/doctor"
cat > "$HANDLERS/demo/install.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'RESULT\tchanged\tdemo\tinstall\t0\t0\tok\n'
SH
chmod +x "$HANDLERS/demo/install.sh"
cat > "$HANDLERS/demo/doctor.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'RESULT\tchanged\tdemo\tdoctor\t0\t0\tok\n'
SH
chmod +x "$HANDLERS/demo/doctor.sh"

export DOTF_HANDLERS_DIR="$HANDLERS"
# write_test_plan writes a minimal registry; point load_registry at it.
export DOTF_REGISTRY_PATH="$TMP_HOME/modules.yaml"
export DOTF_PROFILES_PATH="$TMP_HOME/profiles.yaml"
echo '{"version":1,"default":"smoke","profiles":{"smoke":{"modules":[],"includes":[]}}}' > "$TMP_HOME/profiles.yaml"

PYTHONPATH="$ROOT/scripts:$ROOT/tests" python3 - "$TMP_HOME/plan.json" "$HANDLERS" <<'PY'
import sys
from pathlib import Path
from plan_test_helpers import write_test_plan
plan = Path(sys.argv[1])
handlers = Path(sys.argv[2])
write_test_plan(plan, handlers, [
    ("install", "demo"),
    ("doctor", "demo"),
])
print("plan written:", plan)
PY

echo "==> run_plan"
bash scripts/run_plan.sh --yes --plan-file "$TMP_HOME/plan.json" \
    >"$TMP_HOME/run.log" 2>&1 || { echo "run_plan failed:"; cat "$TMP_HOME/run.log"; exit 1; }
tail -5 "$TMP_HOME/run.log"

STATE="$XDG_STATE_HOME/dotf/modules-state.yaml"
test -f "$STATE" || { echo "state file missing: $STATE" >&2; exit 1; }
echo "--- state file ---"
cat "$STATE"

PYTHONPATH="$ROOT/scripts:$USER_SITE" python3 - "$XDG_STATE_HOME" <<'PY'
import sys
from pathlib import Path
from dotf_core import modules_state as ms
records = ms.load_state(state_home=Path(sys.argv[1]))
assert "demo" in records, f"expected demo installed, got {records}"
r = records["demo"]
assert r.installed, f"expected installed=True, got {r.installed}"
print("state post-install: installed OK (doctor is no-op)")
PY

echo "==> modules_state round-trip"
PYTHONPATH="$ROOT/scripts:$USER_SITE" python3 - <<'PY'
import os, sys, tempfile
from pathlib import Path
from dotf_core import modules_state as ms
with tempfile.TemporaryDirectory() as td:
    os.environ['XDG_STATE_HOME'] = td
    ms.apply_result("foo", "install", "changed")
    ms.apply_result("foo", "config", "changed", manifest_managed=2)
    r = ms.load_state(state_home=Path(td))['foo']
    assert r.installed and r.configured and r.manifest_managed == 2, r
    ms.apply_result("foo", "deconfig", "changed")
    r = ms.load_state(state_home=Path(td))['foo']
    assert r.installed and not r.configured, r
    ms.apply_result("foo", "uninstall", "changed")
    assert 'foo' not in ms.load_state(state_home=Path(td))
    print("round-trip OK")
PY

if PYTHONPATH="$ROOT/scripts:$USER_SITE" python3 -c "import textual" 2>/dev/null; then
    echo "==> TUI app import"
    PYTHONPATH="$ROOT/scripts:$USER_SITE" python3 -c "
from dotf_tui.app import DotfTuiApp, ModulesPane, SkillsPane, McpPane, StatusPane, ConflictsPane, ConfirmModal, ProgressModal
print('app+views import OK')
"

    echo "==> non-TTY __main__ fail-fast"
    PYTHONPATH="$ROOT/scripts:$USER_SITE" python3 - <<'PY'
import sys
from dotf_tui import __main__ as cli
sys.stdin = open('/dev/null')
sys.stdout = open('/dev/null', 'w')
rc = cli.main([])
assert rc == 2, f"expected 2, got {rc}"
print("non-TTY fail-fast: rc=2 OK")
PY

    echo "==> TUI Pilot smoke"
    PYTHONPATH="$ROOT/scripts:$USER_SITE" python3 - <<'PY'
import asyncio
from pathlib import Path
from textual.widgets import Input
import dotf_tui.app as app_mod

async def main():
    captured = []
    async def _capture(action, *, on_line=None):
        captured.append(tuple(action.argv))
        return 0, "ok"
    app_mod.exec_selected_action = _capture
    app = app_mod.DotfTuiApp(Path.cwd())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        pane = app.active_pane
        await pilot.press("slash")
        await pilot.pause()
        pane.query_one("#filter", Input).value = "grepom"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("i")
        for _ in range(40):
            if captured and isinstance(app.screen, app_mod.ProgressModal) and app.screen._done:
                break
            await pilot.pause()
    assert captured, "exec_selected_action not invoked"
    assert any("--install" in a for a in captured), captured
    print("pilot action OK:", captured[0])

asyncio.run(main())
PY
else
    echo "==> TUI checks skipped (textual not installed)"
fi

echo "✓ TUI smoke passed (HOME=$HOME)"
