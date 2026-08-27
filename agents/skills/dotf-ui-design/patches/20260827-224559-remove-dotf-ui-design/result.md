# Result

- target: agents/skills/dotf-ui-design
- patch: 20260827-224559-remove-dotf-ui-design
- risk: high
- status: applied
- applied-at: 2026-08-27T22:46:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m pytest tests/test_agents_sync_references.py tests/test_readme_sync.py tests/test_agents_boundary.py -q` → 15 passed
- privacy check: pass

## Notes

- 已删除 `agents/skills/dotf-ui-design/` 下全部生产内容（SKILL.md、README.md、references/ 下所有 refer skill、脚本与数据）。
- 同步清理了两处引用：
  - `agents/README.md`：从示例条目中移除 `dotf-ui-design`。
  - `agents/skills/role-based-reviewer/references/constraints.md`：将 design 角色典型下游由 `dotf-ui-design` 改为 `按项目 UI 设计规范执行`。
- 运行中生成的 `__pycache__/*.pyc` 为未跟踪文件，已手动删除，不进入 patch。
- patch 目录 `agents/skills/dotf-ui-design/patches/20260827-224559-remove-dotf-ui-design/` 作为审计记录保留；其余目录已清空。
- 应用后变更已自动进入 git index（staged）。
- 仓库中除本 patch 目录外，已无 `dotf-ui-design` 引用。
