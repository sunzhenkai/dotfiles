"""夹具自身行为。"""

from __future__ import annotations

import os
from pathlib import Path


def test_xdg_vars_point_under_tmp_home(tmp_home: Path, tmp_state_dir: Path) -> None:
    assert Path(os.environ["HOME"]) == tmp_home
    assert Path(os.environ["XDG_STATE_HOME"]).is_relative_to(tmp_home)
    assert Path(os.environ["XDG_CONFIG_HOME"]).is_relative_to(tmp_home)
    assert tmp_state_dir.is_relative_to(Path(os.environ["XDG_STATE_HOME"]))
