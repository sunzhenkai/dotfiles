# Result

- target: agents/skills/project-spec-mirror
- patch: 20260828-160733-recovery-projections
- risk: high
- status: applied
- applied-at: 2026-08-28T08:15:01Z

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 25 tests OK
- privacy check: pass

## Notes

已应用五个恢复投影顶层（`context/` `data/` `surface/` `runtime/` `build/`）及 `surface/config.md`；验收改为只凭镜像能重建可运行系统。VERIFY/TRAFFIC 在单实现时不再整页「不适用」。`facets/contracts/runtime.md` 未改名。已有镜像下次 update 须先补这六个骨架文件，否则 `validate` 失败。实际 diff 与 proposal / `change.patch` 一致。未执行 sync / commit / push。
