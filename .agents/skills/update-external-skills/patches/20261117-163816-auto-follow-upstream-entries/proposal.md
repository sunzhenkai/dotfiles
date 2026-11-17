# 重锁自动跟进上游增删条目

- target: .agents/skills/update-external-skills
- mode: update
- patch: 20261117-163816-auto-follow-upstream-entries
- risk: medium
- status: proposed

## Intent

`src/agents/lock_update.py` 已改为在重锁时按锁内条目父目录扫描上游 `SKILL.md`：新出现的子目录补成条目（占位后用 `_promote` 重算哈希、复用同一审计脚本），消失的子目录从锁里删掉，两处变动同时写回 `agents/skills.lock.yaml` 与 `agents/skills.yaml`（新增一律 `optional: true`）。正文目前仍写着「本 skill 只刷新已有条目的 revision」「改名要手写种子条目」「增删条目不在本流程」，与实际行为相反，会让使用者手工补一遍、或误判自动动作需要人跟。

本次把第 1 步、第 2 步、坑 12 与「边界」改写成工具的现状：自动增删的范围、终端三行输出的含义、`optional: true` 的默认、`blocked` 里可能混着新条目、以及仍需人判断的三个缺口（默认安装面、缺 group、overlay 启用状态）。

## Conflict check

只改本 skill 正文，不动 `src/agents/*`、`Makefile`、`lock_verify.py`，也不改其他 skill。收尾授权边界（下发/提交/推送不在流程内）保持不变。

## Rationale

正文是 agent 与人的唯一判读入口，行为已变而正文没变时，代价是一次手工补种子和一次误诊「为什么编目里没有这个 skill」。坑 12 前半段记录的是旧实现（硬失败 + 手写种子），保留会让人继续照做，因此改写成「现在自动处理，剩三个手工缺口」，并在末尾标注旧做法仅在工具出问题时使用。

## Files

- .agents/skills/update-external-skills/SKILL.md：frontmatter description、第 1 步新增条目集说明、第 2 步 `added`/`removed` 解读、坑 12 重写、补坑 17/18、「边界」首条与末条。

## Validation

- 应用前 `git apply --check --recount`。
- 应用后 `git diff --check -- .agents/skills/update-external-skills`，核对 frontmatter。
- 仓库侧不新增测试；`make registry validate` 与 `python3 -m pytest tests/test_lock_update.py -q` 已在代码侧跑过（15 passed）。
