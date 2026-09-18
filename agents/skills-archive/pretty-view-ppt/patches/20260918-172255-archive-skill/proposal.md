# 归档 pretty-view-ppt 至 skills-archive

- target: agents/skills/pretty-view-ppt
- mode: update
- patch: 20260918-172255-archive-skill
- risk: high
- status: proposed

## Intent

用户要求「移除 pretty-view-ppt」；经确认走仓库既有归档约定：skill 生产内容整体移入
`agents/skills-archive/pretty-view-ppt/`（保留生产内容与历史，可恢复），不再是编目内
skill，不参与 `dotf agents -c` 安装。非目标：不改动 `pretty-view-html`；不改动
`~/.agents/skills/` 等安装产物（由用户随后跑 sync 清理）；不触碰
`skills-store` 的历史 `patches/` 记录。

## Conflict check

- 与 `agents/skills-archive/README.md` 的归档/恢复约定一致，无冲突。
- 编目 `agents/skills.yaml` 的 `dotfiles` 组需同步移除该 id，否则编目条目悬空。
- `scripts/ci/shellcheck-first-party.sh` 的排除路径与 `tests/test_ci_contract.py`
  的对应断言需同步改到归档新路径，否则归档后 vendored shell 脚本会被 shellcheck 扫到。
- `agents/README.md` 示例条目段与归档 README 的条目表需同步；skills-store 的
  「已知误报」示例指针需改指归档路径。

## Rationale

按仓库约定下线 skill 应归档而非物理删除，保留可恢复性与审计历史；配套引用不改会让
CI / 编目校验悬空。改动可验证：patch 校验、删除后无残留、pytest 相关用例通过。

## Files

- `agents/skills/pretty-view-ppt/**`（change.patch 内）：删除全部生产文件（SKILL.md、
  README.md、references/、scripts/、tests/），路径前缀均为 `agents/skills/pretty-view-ppt/`。
- 应用后以仓库级步骤补齐（不在 change.patch 内，因路径越出目标 skill 前缀）：
  - `git archive` 将 HEAD 内容落到 `agents/skills-archive/pretty-view-ppt/`（保留 exec 位）
  - `agents/skills.yaml`：移除 `dotfiles` 组的 `- pretty-view-ppt` 条目
  - `agents/README.md`：示例条目段移除 pretty-view-ppt 描述
  - `agents/skills-archive/README.md`：条目表新增一行下线记录
  - `scripts/ci/shellcheck-first-party.sh`：排除路径改指归档路径
  - `tests/test_ci_contract.py`：同步更新断言路径
  - `agents/skills/skills-store/SKILL.md`：已知误报示例指针改指归档路径
  - 本 patch 记录目录随 skill 移入归档路径

## Validation

- 应用前：`git apply --check --recount` 通过
- 应用后：`git diff --check` 通过；`agents/skills/pretty-view-ppt/` 下除本记录外无残留
- `python3 -m pytest -q tests/test_ci_contract.py tests/test_agents_skill_defaults.py
  tests/test_skills_map.py tests/test_desired_set.py tests/test_desired_ops.py` 通过
- 全量 `python3 -m pytest -q` 通过（或失败项与本改动无关且在基线已存在）
