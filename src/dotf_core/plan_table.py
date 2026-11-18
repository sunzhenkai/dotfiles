"""从 validator 的 TSV 渲染计划表。

run_plan.sh 把 ``plan_protocol validate --emit-tsv`` 的输出从 stdin 传进来，
避免 bash 侧再写一份列宽/对齐逻辑：

    python3 -u -m dotf_core.plan_table <"$NORMALIZED"
"""

from __future__ import annotations

import sys
from collections.abc import Iterable

from . import planner


def parse_tsv(lines: Iterable[str]) -> tuple[str, str, list[planner.PlanAction]]:
    os_id = ""
    profile = ""
    actions: list[planner.PlanAction] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if not line:
            continue
        kind, _, rest = line.partition("\t")
        if kind == "META":
            fields = rest.split("\t")
            os_id = fields[0] if fields else ""
            profile = fields[1] if len(fields) > 1 else ""
        elif kind == "ACTION":
            fields = rest.split("\t")
            if len(fields) >= 4:
                actions.append(
                    planner.PlanAction(
                        module=fields[2],
                        action=fields[1],
                        reason=fields[3],
                        index=int(fields[0]),
                    )
                )
    return os_id, profile, actions


def render(lines: Iterable[str]) -> str:
    os_id, profile, actions = parse_tsv(lines)
    out = planner.format_plan_header(os_id, profile, len(actions))
    if actions:
        out.extend(planner.format_plan_table(actions))
    else:
        out.append("（空计划）")
    return "\n".join(out)


def main() -> int:
    print(render(sys.stdin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
