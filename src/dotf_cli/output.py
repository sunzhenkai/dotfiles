"""输出契约：--json 双模序列化（spec: cli-surface）。

人类输出由各命令直接打印；本模块只负责 JSON 模式的统一文档形状。
"""

from __future__ import annotations

import json
import sys

from .errors import payload


def emit_result(command: str, data, json_mode: bool) -> None:
    """成功结果。人类模式下 data 已由命令直接输出，这里只兜底空 data。"""
    if json_mode:
        _dump({"ok": True, "command": command, "data": data if data is not None else {}})


def emit_error(command: str, err, json_mode: bool, verbose: bool) -> None:
    if json_mode:
        doc = payload(err, verbose)
        doc["command"] = command
        _dump(doc)
    else:
        from .errors import render

        print(render(err, verbose), file=sys.stderr)


def _dump(doc: dict) -> None:
    print(json.dumps(doc, ensure_ascii=False))
