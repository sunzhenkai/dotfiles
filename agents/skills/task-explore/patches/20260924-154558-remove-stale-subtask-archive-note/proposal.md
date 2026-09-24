# task-explore：清除「子任务原地归档」残留表述

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-154558-remove-stale-subtask-archive-note
- risk: low
- status: proposed

## Intent

`SKILL.md` 索引小节仍有一句引用已删除的「子任务原地归档」概念（handoff 解耦后子任务不再原地归档），删除该半句。无行为变化。

## Conflict check

none —— 与 20260924-154507-decouple-handoff-archive 同方向收尾。

## Rationale

上一轮 patch 漏改；残留文本会误导 agent 以为子任务仍有独立归档形态。

## Files

- `agents/skills/task-explore/SKILL.md`（索引小节一行）

## Validation

- 应用前 `git apply --check --recount`；应用后 `grep 原地归档` 无命中。
