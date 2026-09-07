"""``python3 -m dotf_tui`` — TTY-only manager skin.

The TUI runs entirely in-process; it spawns ``bin/dotf`` subcommands for each
action and never writes HOME / overlay / state itself. The CLI ``dotf tui``
delegates here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_ROOT = _SCRIPTS.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _die(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    del argv
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return _die(
            "dotf tui 需要 TTY。请改用 CLI，例如: "
            "dotf nvim --deconfig 或 dotf agents skill apply <id>",
            2,
        )
    try:
        from .app import _missing_textual_message, build_app
    except Exception as exc:  # pragma: no cover - import-time diagnostic
        return _die(str(exc), 1)
    try:
        app = build_app(_ROOT)
    except RuntimeError as exc:
        return _die(str(exc), 1)
    except ImportError as exc:
        return _die(_missing_textual_message() + f"\n[{exc}]", 1)

    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
