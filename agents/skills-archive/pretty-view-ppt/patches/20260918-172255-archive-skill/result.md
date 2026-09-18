# Result

- target: agents/skills/pretty-view-ppt
- mode: update
- patch: 20260918-172255-archive-skill
- risk: high
- status: applied
- applied-at: 2026-09-18T17:23:00+08:00

## Validation

- `git apply --check --recount`: pass（应用后另以 `git apply -R --check --recount` 复核工作树删除与 patch 完全一致）
- `git diff --check`: pass
- target tests: `python3 -m pytest -q tests/test_ci_contract.py tests/test_agents_skill_defaults.py tests/test_skills_map.py tests/test_desired_set.py tests/test_desired_ops.py` → 46 passed；`bash scripts/ci/shellcheck-first-party.sh` → selected=93 excluded_third_party=2（归档新路径生效）
- privacy check: pass（无新增内容；删除/移动均不含敏感信息）
- mode check: pass（update；归档非 self-upgrade）

## Notes

- 用户确认走归档：生产内容经 `git archive HEAD` 落入 `agents/skills-archive/pretty-view-ppt/`（保留 exec 位），本 patch 删除 `agents/skills/pretty-view-ppt/` 全部 180 个生产文件，原目录已无残留。
- 仓库级配套改动（change.patch 之外，路径越出目标 skill 前缀，见 proposal.md）：`agents/skills.yaml` 移除编目条目；`agents/README.md` 示例条目段清理；`agents/skills-archive/README.md` 条目表新增下线记录；`scripts/ci/shellcheck-first-party.sh` 与 `tests/test_ci_contract.py` 的排除/断言路径改指归档路径；`agents/skills/skills-store/SKILL.md` 已知误报示例指针改指归档路径。
- 未触碰：`skills-store` 历史 `patches/`、`~/.agents/skills/` 等安装产物（需用户跑 `dotf agents -c` 清理本机已安装副本）。
- 应用后 `git status` 呈「原路径 180 个未暂存删除 + 归档路径未跟踪新增」，由用户审阅后自行 commit。
