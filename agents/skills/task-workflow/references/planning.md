# 规划阶段：new / explore / design / propose

执行任一阶段前读根 `SKILL.md`；遵守 `safety.md` 的 RES-1/2、PLAN-1、PROXY-1/2。规划阶段只读目标代码与文档，不执行 Checkout Gate，不为 task 分支检查或修改目标仓 Git 状态。

## 公共步骤

- 除 `task-new` 外，第一步运行 `resolve`：本条或会话已有唯一编号时显式传入，否则用 `--infer --hint`，退出码 2 时原样展示并停止。
- 从 `resolve` / `new` JSON 读 `workflow_notes`；存在时视为跨任务硬约束。
- 只维护 README 的计划涉及面；工作上下文保持“尚未准备（apply 时执行 Checkout Gate）”。status 与 INDEX 只通过 taskctl 更新。

## 委托 openspec-* 的绑定契约

委托任何 `openspec-*` skill 前必须同时具备两项绑定：**在该 target 的 canonical `planning_root` 下执行**，并**显式给出 change name**。缺任一项不得委托——openspec CLI 只认 cwd 最近的 `openspec/`，无绑定会写错位置或反问用户选 change。无法确定时停下报告该 target。

本工作流不支持 standalone store：`关联 OpenSpec` 表不再有 store 列；change 位于独立 store 时立即以 unsupported-store 报告并停止，不把失败推迟到 apply。旧模板的空 store 列仍可解析。

## task-new

1. Agent 从 `[TASK_NEW_INPUT_START]` 后的用户正文归纳一句需求；正文确实为空才问“要做什么？”。自行生成简体中文 title 与英文 kebab-case slug，不追问 slug，也不把自然语言提取交给脚本。
2. 读 notes 的默认涉及面，区分必须（会修改）、建议（只读）、排除；对照目标记录现状缺口，信息不全写待确认，不因此阻止创建。
3. 运行 `new --title ... --slug ...`，随后补全 README 的概述、背景、目标、现状缺口、涉及面、验收标准与“尚未准备”的工作上下文。
4. 输出 ID、路径、缺口和下一步：方案未定走 explore，范围已清走 propose。

## task-explore

1. resolve 后读 README、notes 与已有 OpenSpec 上下文。
2. 委托 `openspec-explore` 澄清问题、方案和范围，不写业务代码。
3. 结论写入 README「方案笔记」小节（备选方案、取舍、否决理由、未决问题）并记入变更记录；draft 才更新为 `exploring`。
4. 有架构分叉走 design；路径唯一走 propose。

## task-design

1. resolve 后再读 skill `task-design`，并读 README 与 explore 结论。
2. 只写 `<taskRoot>/design/`：`README.md` 索引、归档落点表和设计正文；不写目标仓正式 docs、ADR、knowledge 或业务代码。
3. 在 task README 记录设计文件与计划落点，status 更新为 `designed`，输出 staged 路径、落点、未决问题和 propose 桥接。

## task-propose

1. resolve 后把 task README、notes 和可选 `design/` 作为提案输入。
2. 单仓 change 写入该仓 planning root；跨仓/工作区级 change 写入工作区 planning root。这里只记录 canonical planning root，不绑定实现 checkout。
3. 对每个 change 按上文绑定契约委托 `openspec-propose`，生成 apply-ready artifacts。
4. 更新 README「关联 OpenSpec」前先读实际小节，只替换最小唯一锚点；失败后重新读取，不猜标题或空白。
5. 写入每个 change 的名称、canonical 仓、相对路径与顺序（小整数，多 change 时决定推进先后；缺省按表行序）。
6. 收尾门：对每个 change 在其 `planning_root` 下运行 `openspec validate --strict --change <name>`，全部通过后 status 才更新为 `proposed`；失败原样报告并停止。
7. 输出 change 列表和 `task-apply` 桥接，并说明 Checkout Gate 尚未执行。

**产物如何进入 apply**：change 写在 canonical planning root，apply 一律在该处读取与勾选，不需要先提交到交付分支，也不随 worktree 移动。propose 之后留下的未提交 planning 产物在 apply 准备时是非阻塞诊断，不是 dirty 阻断。
