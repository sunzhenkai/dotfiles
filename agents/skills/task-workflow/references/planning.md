# 规划阶段：new / explore / design / propose

执行前读根 `SKILL.md` 与 `safety.md`（RES-1/2、PLAN-1、PROXY-1）。规划阶段只读目标代码与文档，**不切分支、不为 task 分支查改 Git 状态**（工作上下文保持「尚未准备」）。

## 公共步骤

- 除 `task-new` 外，第一步 `resolve`：本条或会话已有唯一编号时显式传入，否则用 `--hint`；退出码 2 时原样展示候选并停止。
- 从 `resolve` / `new` 的 `workflow_notes` 读跨任务硬约束。
- status 与 INDEX 只通过 taskctl 更新；README 正文由 Agent 写。

## 委托 openspec-* 的绑定契约

`openspec-*` skill 由目标仓自己跑 `openspec init --tools <agent>` 生成，**不是所有仓都有**。委托前先确认它在当前 agent 环境可用；不可用就停下报告并给出可选项（在目标仓 init，或改用 CLI 直调路径），**不要自行发明等价命令**——archive 的 CLI 直调路径见 `archive.md`，规划阶段没有对应替代。

可用时，委托必须同时具备两项绑定：**在该 change 的 `planning_root` 下执行**，并**显式给出 change name**。缺任一项不得委托——openspec CLI 只认 cwd 最近的 `openspec/`，无绑定会写错位置或反问用户选 change。无法确定时停下报告。

## task-new

1. Agent 从 `[TASK_NEW_INPUT_START]` 后的用户正文归纳一句需求；正文确实为空才问「要做什么？」。自行生成简体中文 title 与英文 kebab-case slug，不追问 slug。
2. 读 notes 的默认涉及面，区分必须（会修改）、建议（只读）、排除。
3. 跑 `new --title ... --slug ...`，然后补全 README 的概述、涉及面与验收标准。信息不全的写「待确认」，不因此阻止创建。
4. 输出 ID、路径、待确认项和下一步：方案未定走 explore，范围已清走 propose。

## task-explore

1. resolve 后读 README、notes 与既有 OpenSpec 上下文。
2. 委托 `openspec-explore` 澄清问题、方案和范围，不写业务代码。
3. 结论写入 README 新增的「方案笔记」小节（备选方案、取舍、否决理由、未决问题）并记入变更记录；`draft` 才 `set-status <id> exploring`。
4. 有架构分叉走 design；路径唯一走 propose。

## task-design

1. resolve 后再读 skill `task-design`，并读 README 与 explore 结论。
2. 只写 `<taskRoot>/design/`：`README.md` 索引、归档落点表和设计正文。不写目标仓正式 docs、ADR、knowledge 或业务代码。
3. 在 task README 记录设计文件与计划落点，`set-status <id> designed`，输出 staged 路径、落点、未决问题和 propose 桥接。

## task-propose

1. resolve 后把 task README、notes 和可选 `design/` 作为提案输入。
2. 决定每个 change 的 canonical planning root：单仓 change 写该仓，跨仓或工作区级 change 写工作区根。这里只记录 planning root，不绑定实现 checkout。
3. 按上文绑定契约对每个 change 委托 `openspec-propose`，生成 apply-ready artifacts。
4. 更新 README「关联 OpenSpec」表：change 名称、相对路径、仓库（工作区根写 `.`）、说明。改表前先读实际小节，只替换最小唯一锚点。
5. 收尾门：对每个 change 在其 `planning_root` 下跑 `openspec validate --strict --type change <name>`，全部通过后才 `set-status <id> proposed`；失败原样报告并停止。
6. 输出 change 列表与 `{{slash:task-apply}}` 桥接，并说明分支尚未准备。

**产物如何进入 apply**：change 留在 canonical planning root，apply 一律在该处读取与勾选，不需要先提交到交付分支。propose 留下的未提交 planning 产物不影响 `prepare-branches`——它只看 `必须` 仓。
