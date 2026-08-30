# 让自检表随安装分发

- skill: project-spec-mirror
- risk: medium
- 依据: skill-creator「progressive disclosure：reference 要能在运行现场被读到」

## 问题

`scripts/agents/sync.py` 的 `install_skill_sidecars` 只把 `SKILL.md`、`references/`、`scripts/`
装到 agent 目录。而 SKILL.md 的「质量检查」要求读 `evals/README.md`、核对 `evals/cases.yaml`，
并运行 `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`。

安装态下这两个路径都不存在，第 2 条还写死了源仓库的目录布局，在别的机器上不成立。
结果是这个 Skill 唯一的交卷前自检闭环在真实运行现场必然静默跳过，
而 `evals/cases.yaml` 已积累到 394 行、比 SKILL.md 长一倍多，投入没有回报。

## 改动

1. 新增 `references/checklist.md`：按「安全与边界 / 状态机 / 粒度 / 路由与覆盖 / 交付」
   五组给出交卷前自检项，随 sync 分发。条目来自 `evals/cases.yaml` 中影响输出的硬约束，
   写成可核对的陈述句而非 case 结构，不复制整份 yaml。
2. SKILL.md「质量检查」改为对照 `references/checklist.md`，并显式说明
   `examples/` `evals/` `experience/` `tests/` 是源仓库资产、不随安装分发；
   unittest 路径改为 `<skill-dir>` 占位，去掉写死的仓库布局。
3. `tests/test_skill_contract.py` 把 `references/checklist.md` 纳入存在性检查，
   并新增断言：SKILL.md 必须引用 checklist、不得再出现写死的仓库路径，
   checklist 必须覆盖脱敏、状态回写、覆盖率与图表四类关键标记。

## 非目标

- 不改 `scripts/agents/sync.py`（不在本 Skill 目录内，超出 pwd-skill-manager 边界）。
- 不删除 `evals/cases.yaml`；它继续作为源仓维护态的完整回归集。
- 不改动金字塔、恢复投影、切面或 specctl 行为。

## 验证

- `git apply --check --recount`
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
- 人工核对 checklist 条目均可在 SKILL.md 或 references 中找到依据
