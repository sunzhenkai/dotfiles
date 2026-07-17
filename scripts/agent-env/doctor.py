#!/usr/bin/env python3
"""兼容入口：委托统一 agents doctor。

请优先使用:
  python3 scripts/agents/doctor.py
  dotf -c agents --doctor
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

print(
    "提示: scripts/agent-env/doctor.py 为兼容层，请改用: python3 scripts/agents/doctor.py",
    file=sys.stderr,
)

target = Path(__file__).resolve().parent.parent / "agents" / "doctor.py"
raise SystemExit(subprocess.call([sys.executable, str(target), *sys.argv[1:]]))
