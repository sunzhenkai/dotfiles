# 任务文档骨架

`new` 时按此创建 `{taskRoot}/TASK.md`。按已知信息填写，未知留空，不要编造。

`save` 时更新同一文件：改 `updated` 与有变化的章节，不要整文件重写后丢掉仍有效的内容。同时同步 `tasks/INDEX.md` 对应行（标题、日期、一句话目标），不要把进展抄进索引。

```markdown
# <Title>

- slug: <task-name>
- status: ongoing
- created: YYYY-MM-DD
- updated: YYYY-MM-DD

## 目标

- [要达成什么]

## 非目标

- [明确不做的]

## 现状

[已知事实、已读材料、约束。链到代码或文档路径。]

## 进展

- YYYY-MM-DD：[本轮结论，一条一事]

## 决策

- 采纳：[方案名] — [主因]
- 取舍：[接受 / 放弃]
- 带进实现的未决：[列表，或无]
- 回退：[选错了怎么撤]

## 交接

- driver: `{task-name}-driver`（handoff 后填写）
- 归档路径：[handoff / archive 后填写]

## 未决问题

- [ ] [还不知道的]

## 下一步

- [explore / chat / design / decide / handoff / archive / 其它]
```

归档前把 `status` 改为 `archived`，并在元信息中加上 `archived: YYYY-MM-DD`。handoff 成功后再加 `handed-off: YYYY-MM-DD` 与 `driver: {task-name}-driver`。
