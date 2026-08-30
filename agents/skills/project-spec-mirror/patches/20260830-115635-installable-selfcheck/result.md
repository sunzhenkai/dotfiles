# 结果

- status: applied
- applied_at: 2026-08-30 11:58 (UTC+8)

## 实际改动

| 文件 | 变化 |
|------|------|
| `references/checklist.md` | 新增 55 行，五组交卷前自检项 |
| `SKILL.md` | 「质量检查」改为对照 checklist；声明源仓资产不随安装分发；unittest 路径改 `<skill-dir>` 占位 |
| `tests/test_skill_contract.py` | checklist 纳入 reference 存在性检查；新增 `test_checklist_is_the_installable_selfcheck` |

## 验证

- `git apply --check --recount`：通过
- `git apply --recount`：通过
- `git diff --check`：无空白错误
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`：50 tests OK

## 偏差

无。实际 diff 与 proposal 一致，未夹带无关改动，未触碰 `scripts/agents/sync.py` 与 `evals/cases.yaml`。

## 遗留

`evals/cases.yaml` 与 `references/checklist.md` 存在同源约束的两份表述，靠
`test_checklist_is_the_installable_selfcheck` 的标记断言做弱防漂移。若后续 checklist 条目增多，
考虑由 cases.yaml 生成 checklist，而不是双份手工维护。
