# 闭环门禁与 CLI 减负

- target: agents/skills/project-spec-mirror
- patch: 20260905-211617-optimize-closed-loop
- risk: high
- status: proposed

## Intent

按已批准的优化列表收紧闭环、减负 CLI，并补上可验证门禁：

1. 空骨架不能 `built`；`finalize` 是唯一对外收尾。
2. 旧树报 `layout=legacy`，阶段为 `rebuild`。
3. `reconstructable` 未映射代码入口必须进 source-map 或 INDEX「未指定」。
4. 对外只留 6 个命令；死字段离开状态；能力状态只有 `draft` | `ready`。
5. update 未消化 `unmapped`、rename 回写、briefing 泄漏、非 git 入口漂移均可被 CLI 拦住或报出。

非目标：不恢复档 C / 模块文件表 / concise|detailed；不写目标仓 `openspec/`。

触发：用户要求完成该优化列表。

## Conflict check

- 与上一轮对外 12 命令、`set-sync --built` 可标 built、briefing 空骨架可 finalize 直接冲突：这正是本轮要改的门禁。
- 与 OpenSpec change 工作流：仍禁止写入 `openspec/`。
- 与 inventory/symbols 探测能力：函数保留，不再作为对外子命令。

## Rationale

上一轮双读者树已落地，但仍能把空骨架标成 built、旧树被当成 update、coverage 只数「≥1」。把门禁收到 `finalize`、把 CLI 收到 6 个命令后，交卷条件可测、Skill 主路径可读。跨项目仍成立。

## Files

- `SKILL.md` — 6 命令、阶段、禁写、draft/ready
- `references/layout.md` — 目录 + 模式 + finalize 门
- `references/routing.md` — rename 回写与 unmapped 消化
- `references/checklist.md` — finalize 与复现抽检
- `references/appendix.md` — facets/realization，默认不读
- `references/diagrams.md` `modes.md` `knowledge.md` `facets.md` `projections.md` — 缩短或改指针
- `examples/minimal-checkout.md` — 最小交卷例
- `scripts/specctl.py` — layout、coverage、route、finalize、命令表
- `tests/` `evals/cases.yaml` — 对齐新契约

## Validation

- `git apply --check --recount` 通过后再 apply
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
- 逐条核对照优化列表 P0–P2
