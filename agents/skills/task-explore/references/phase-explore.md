# explore 阶段

进入本阶段后执行。未绑定任务则先回到 `SKILL.md` 的绑定规则。

针对任务，不断探索预期目标。**只委托 `grilling`。** 禁止调用 `grill-with-docs` 或 `domain-modeling`：它们会写仓库根 `CONTEXT.md` / `docs/adr/`，与任务目录落点冲突。

1. 必须已绑定任务；否则先走绑定。
2. 先读 `TASK.md`、已有 `glossary.md` 与 `design/`。
3. 读取并遵循 `grilling`。不可用则用它的轮次格式当面问；**不要发明等价命令**，也不要改调 `grill-with-docs`。
4. 问的是**预期目标、成功标准、范围、约束、未知**。事实自己查，决策交给用户。
5. 发现任务含多个可独立推进的方向时，**提示一次**可 `split` 拆子任务，不阻断、不自动创建；用户确认后走 `split`。
6. 术语结晶时由本 skill 写入 `{taskRoot}/glossary.md`；独立决策写入 `{taskRoot}/design/adr-<slug>.md`。禁止写仓库根 `CONTEXT.md`、`docs/adr/`。
7. 结束本轮时列出已澄清目标与仍开放的 frontier，并提示是否 `save`。

术语/ADR 可当时写入任务目录；那不是对 `TASK.md` 的替代，进展仍要按主文件提示是否更新任务文档。
