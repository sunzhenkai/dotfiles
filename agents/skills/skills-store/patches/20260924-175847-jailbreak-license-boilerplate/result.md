# Result

- target: agents/skills/skills-store
- mode: update
- patch: 20260924-175847-jailbreak-license-boilerplate
- risk: medium
- status: applied
- applied-at: 2026-09-24T18:05:00+08:00

## Validation

- `git apply --check -R change.patch`: pass（patch 与工作树一致；改动在仓库直接落地，未走 apply 一次）
- `git diff --check`: pass
- `python3 -m pytest -q tests/test_audit_skill.py tests/test_lock_update.py` → 25 passed
  （含本轮新增：MIT `LICENSE` 不命中 `jailbreak_role`；`no restrictions` /
  `without any limits` / `pretend to be` 三条仍 exit 2）
- upstream archify @ `9e35d2b0b39b` 跑 `audit-skill.sh` → exit 1，`jailbreak_role` 零命中，
  仅剩 `internal_url` WARN（文档示例 `git.internal`，误报）
- `make skills-lock-update` → `wrote agents/skills.lock.yaml sources=2 blocked=0`，archify 前进到 `9e35d2b0b39b`

## Notes

误报自 2026-09-23 起每轮重锁都要人工豁免一次（`agents/skills.yaml` 里 archify 条目下有当时的豁免记录）。
archify 是唯一把 `LICENSE` 放进锁内 `subdirectory` 的 source，所以只有它稳定触发。

未采纳的两个更宽方案：整体不扫 `LICENSE`（给「把注入文本藏进 LICENSE」开口子），
或只把 archify 手工豁免（不可复用）。`TEXT_NAMES` 仍含 `LICENSE`，其余规则照常覆盖该文件。

自审（对 skills-store 目录本身跑审计）不作验证：该 skill 的文档逐条列出它检测的关键词，
本轮前即有 26 项自命中。
