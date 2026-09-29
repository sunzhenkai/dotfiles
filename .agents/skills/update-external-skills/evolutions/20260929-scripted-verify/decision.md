# decision — 20260929-scripted-verify

**superseded**（2026-09-29，非否决）

本候选稿（第 2、4 步改调 `src/agents/lock_verify.py`）**已落地**，但不是单独晋升：同日的
`20260929-no-auto-sync` 以本稿为底稿打补丁，两份改动合并成一次晋升写进生产稿。

因此本目录的 `SKILL.md` 停留在合并前状态，与生产稿有 74 行差异——**要读本稿的实际生效内容，
去看 `../20260929-no-auto-sync/SKILL.md` 或生产稿**，不要按本目录候选稿理解。

`src/agents/lock_verify.py`、`Makefile` 的 `skills-verify` target 与
`tests/test_agents_lock_verify.py` 是本稿的产物，已随另一提交进入仓库历史（9 passed）。
