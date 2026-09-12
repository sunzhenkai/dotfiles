"""错误码与退出码契约（spec: cli-surface）。

顺序即退出码：usage=1, env=2, plan=3, handler=4, conflict=5, internal=6。
"""

from __future__ import annotations

CODES = ("usage", "env", "plan", "handler", "conflict", "internal")
EXIT_CODES = {code: i + 1 for i, code in enumerate(CODES)}


class DotfError(Exception):
    """带错误码的 CLI 失败；message 为对用户可读的多行文本。

    rc 允许透传底层工具的原生退出码（如 planner 的契约），
    缺省取错误码表映射值。
    """

    def __init__(
        self,
        code: str,
        message: str,
        chain: list[str] | None = None,
        rc: int | None = None,
    ):
        if code not in EXIT_CODES:
            raise ValueError(f"未知错误码: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.chain = list(chain or [])
        self.rc = rc


def exit_code(code: str) -> int:
    return EXIT_CODES[code]


def render(err: DotfError, verbose: bool = False) -> str:
    """渲染为 stderr 单行前缀 + 原始文案；verbose 追加调用链。"""
    lines = [f"[dotf] {err.code}: {err.message}"]
    if verbose and err.chain:
        lines.append("调用链:")
        lines.extend(f"  {step}" for step in err.chain)
    return "\n".join(lines)


def payload(err: DotfError, verbose: bool = False) -> dict:
    error = {"code": err.code, "message": err.message}
    if verbose and err.chain:
        error["chain"] = err.chain
    return {"ok": False, "error": error}
