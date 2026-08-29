# Result

- target: agents/skills/project-spec-mirror
- patch: 20260830-015759-fix-state-lifecycle
- risk: high
- status: failed
- applied-at: 2026-08-30T01:59:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — fail（37 项中 1 项 error）
- privacy check: pass

## Notes

生产变更已应用；失败仅来自本 patch 新增的测试隔离写法：测试直接调用 `cmd_detect`，但没有经过 `main` 的 `SpecError` 转 JSON 边界，导致预期错误以异常形式逸出。其余 36 项通过。依据 patch 协议，本目录不再改写；修复使用新的独立 patch。
