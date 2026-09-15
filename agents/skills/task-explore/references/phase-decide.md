# decide 阶段

进入本阶段后执行。未绑定则先回到 `SKILL.md` 的绑定规则。

冻结 **探索任务** 的采纳方案。不写实现代码，不创建 OpenSpec change。

## 门禁

缺任一项就停下，建议先 `explore` / `design`：

- `TASK.md` 目标能一句话说清
- 有可推荐方案（通常来自 `design/`；无设计稿则用户必须当面确认选项）
- 成功标准可检验

## 写入

更新 `{taskRoot}/TASK.md` 的 **决策** 小节（见 [task-template.md](task-template.md)）：

- 采纳：方案名 + 一句话主因
- 取舍：接受什么、放弃什么
- 可带进实现的未决：列出；未列出的视为本探索任务内已关闭
- 回退：选错了怎么撤

有独立、难逆的权衡时，另写 `{taskRoot}/design/adr-<slug>.md`。不要写仓库 `docs/adr/`。

同步 `INDEX.md` 对应行的一句话（可改成「已决：…」）。提示是否继续 `handoff`。

## 压缩路径

用户明确说「按 design 里的推荐冻结并交接」：本轮先完成本阶段，再立刻进入 `handoff`，不必再问一次是否 decide。
