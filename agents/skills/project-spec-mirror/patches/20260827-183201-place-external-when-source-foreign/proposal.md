# 外来仓走 spec/<project>/

- target: agents/skills/project-spec-mirror
- patch: 20260827-183201-place-external-when-source-foreign
- risk: medium
- status: proposed

## Intent

修正放置规则：`in-project`（`<host>/spec/`）仅当目标 source / `--project` 就是当前仓。`--source` 指向另一仓，或 `--project` 与当前仓名不同时，一律 `<cwd>/spec/<project>/`。

触发：在聚合工作区 git 根对另一个 project 做镜像时，不再占用当前仓的 `spec/`。

非目标：不迁移已误放的镜像目录；不改金字塔正文、粒度、git 同步指针。

## Conflict check

与原文「只看 cwd 是否 project 根」冲突，这正是本次要改的错误规则。`--in-project` 在目标为外来仓时改为忽略，避免再占 host 的 `spec/`。Eval `placement-in-vs-external` 同步更新。none 以外：与 OpenSpec 边界不变。

## Rationale

跨工作区复用时，工作区本身常是 git 仓。放置必须比较「目标身份」与「当前仓身份」，否则 `--project`/`--source` 只是标签。行为可用 detect/init 测试复现：workspace git 根 + 外来 `--source` → `spec/<project>/`。

## Files

- `agents/skills/project-spec-mirror/scripts/specctl.py` — `detect_layout` / `find_spec_root`
- `agents/skills/project-spec-mirror/SKILL.md` — 放置规则
- `agents/skills/project-spec-mirror/references/layout.md` — spec_root 一句
- `agents/skills/project-spec-mirror/evals/cases.yaml` — placement case
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 外来仓回归

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
