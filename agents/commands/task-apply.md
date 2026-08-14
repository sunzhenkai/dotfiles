---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

对 task 已关联的 OpenSpec change 执行实施：先对必须目标仓跑 Checkout Gate（已在 task 分支则跳过；无关仓与当前仓不切），再委托 `openspec-apply-change`。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-apply` 职责）。机械步骤用 `taskctl`。开始时加载工作区 `.task-workflow.md`（`taskctl notes` 或 `resolve` 的 `workflow_notes`）。

**输入**：任务编号（推荐 `T0001`）等；可省略（自动推断）；可选仅实施部分 change 名；可选分支前缀。

下一步：续作 → `{{slash:task-apply}} TNNNN`；全部完成 → `{{slash:task-archive}} TNNNN`。
