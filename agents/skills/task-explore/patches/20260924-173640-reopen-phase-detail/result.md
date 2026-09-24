# Result

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-173640-reopen-phase-detail
- risk: medium
- status: applied
- applied-at: 2026-09-24T17:38:31+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m pytest agents/skills/task-explore/tests -q` → 39 passed（本 patch 前为 33）
- privacy check: pass
- mode check: pass（`update`）
- 旧矛盾措辞清除：`grep "INDEX 行不动" SKILL.md` → 0 命中
- 未触及历史 `patches/`、`.agents/skills/`、agent 镜像

## Notes

按 proposal 原样应用，无范围偏差。新增 `references/phase-reopen.md`（定位 3 + 门禁 4 + 步骤 6）；SKILL.md 的 reopen 段由 7 步瘦成 4 条硬门禁并加入按需加载表，`chat` / `resume` 仍留「本文件已够」。

实质修掉的是索引谎报：索引小节规定 handed-off 行一句话以 `→ {task-name}-driver` 结尾，而旧 reopen 第 6 步要求撤回交接时「INDEX 行不动」，两者互斥；现按状态定义改为去尾注。顺序不变量测试从读 SKILL.md 段落改读 reference，锁 dest 检查 < 状态改写 < 整树移动。

遗留（不在本轮范围）：`chat` / `resume` 仍无细则文件；reopen 规则尚未提升进 `openspec/specs/task-explore-lifecycle/spec.md`。未执行 `dotf agents -c`。
