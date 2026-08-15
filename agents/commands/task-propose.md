---
id: task-propose
title: "提出提案"
description: 为指定 task 制定提案，委托 openspec-propose，保存一个或多个 changes
category: Workflow
tags: [task, workflow, openspec]
---

为 task 制定 OpenSpec 提案：resolve 后直接委托 `openspec-propose`，并在 README 记录每个 change 的 canonical 仓、相对路径与 store；不检查目标仓 Git 状态或准备分支，Checkout Gate 延后到 `task-apply`。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-propose` 职责）。机械步骤用 `taskctl`（= `python3 <task-workflow skill>/scripts/taskctl.py`；PATH 无此命令，勿直接执行）。开始时加载工作区 `.task-workflow.md`（`taskctl notes` 或 `resolve` 的 `workflow_notes`）。

**输入**：任务编号（推荐 `T0001`）等；可省略（自动推断）。本条未写编号时，若本会话上文已有明确任务，MUST 当作已指定并显式传给 `resolve`，不要只把命令名放进 `--hint` 再让用户选。可选 change 名列表或拆分说明。

下一步：实施方案 → `{{slash:task-apply}} TNNNN`；补充方案 → `{{slash:task-explore}} TNNNN`；补全面设计 → `{{slash:task-design}} TNNNN`。
