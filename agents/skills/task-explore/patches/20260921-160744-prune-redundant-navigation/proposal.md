# 删除重复导航与重复护栏（writing-for-agents 优化）

- target: agents/skills/task-explore
- mode: update
- patch: 20260921-160744-prune-redundant-navigation
- risk: medium
- status: proposed

## Intent

按 writing-for-agents 的「单一真相源 / 相关性」原则删除纯重复内容，不改变任何行为：

1. 删除末尾 `## 相关` 整节：7 个 reference 指针与「进入对应阶段再读，不要一次性打开」已由 `## 加载` 表承载；`grilling` / `taskflow` / `dotf-code-explore` 三个姊妹 skill 关系已分别由 `explore` / `handoff` 阶段小节与 `## 何时不用` 表承载。该节为 100% 重复的导航。
2. 删除 `## 进展提示` 中「不要把整段对话粘进 `TASK.md`」一条：与 `save` 小节的「不要贴聊天记录」同义，写法规则归属执行写入的 `save` 小节。

非目标：不动阶段表、加载表、绑定、索引、各阶段步骤、`何时不用`；不改任何被 `tests/test_task_explore_contract.py` 钉住的文本。

## Conflict check

- 契约测试钉住的字符串（`必须先获得确认再创建`、`应提示创建或者恢复`、`只读该阶段详情`、`不要预加载其它 phase`、四个 phase 文件名、archive/reopen 顺序断言等）均不在本次删除范围内。
- `test_phase_loaded_on_demand` 断言的四个 `references/phase-*.md` 字符串由 `## 加载` 表提供，保留。
- 无其它冲突。

## Rationale

重复导航让同一规则有两处需要同步维护，并稀释正文注意力；删除后所有信息仍各有唯一归属。行为不变，可由契约测试确定性验证。

## Files

- agents/skills/task-explore/SKILL.md — 删 `## 相关` 整节、删 `## 进展提示` 一条重复护栏

## Validation

- 应用前：`git apply --check --recount`（已通过）
- 应用后：`git diff --check`；`python3 -m unittest` 跑 `tests/test_task_explore_contract.py` 全量；frontmatter `name` 与目录名一致
