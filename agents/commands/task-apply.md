---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

对 task 已关联的 OpenSpec change 执行可恢复实施：Checkout Gate 续用已绑定 worktree/checkout，`execution-context` 定位每个 change，并在开始、每项完成、暂停和测试时强制 checkpoint。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-apply` 职责）。机械步骤用 `taskctl`。开始时加载工作区 `.task-workflow.md`（`taskctl notes` 或 `resolve` 的 `workflow_notes`）。

**输入**：任务编号（推荐 `T0001`）等；可省略（自动推断）。本条未写编号时，若本会话上文已有明确任务，MUST 当作已指定并显式传给 `resolve`，不要只把命令名放进 `--hint` 再让用户选。可选仅实施部分 change 名；可选分支前缀。

**不得提前结束**：除非全部完成、遇到需要用户决策的阻塞或用户中断。结束前 MUST 写 `taskctl checkpoint`；续作先读 `execution-context` / `progress.md`，从未完成 checkbox 继续，不重复已完成项。

下一步：续作 → `{{slash:task-apply}} TNNNN`；全部完成 → `{{slash:task-archive}} TNNNN`。
