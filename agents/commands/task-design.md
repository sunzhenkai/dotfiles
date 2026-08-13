---
id: task-design
title: "任务设计"
description: 复杂任务的可选全面设计；文档写入该 task 的 design/，归档时再晋升
category: Workflow
tags: [task, workflow, design]
---

在已解析的 task 上下文中做决策级设计（不写业务代码）。resolve 后先 Checkout Gate；文档只写入该 task 的 `design/`；`task-archive` 时再晋升到 `docs/design` / ADR / knowledge。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-design` 职责），再读 skill `task-design`（设计方法）。机械步骤用 `taskctl`。

**输入**：任务编号（推荐 `T0001`）、slug 或路径；可省略（自动推断）；可选设计焦点。

下一步：固化提案 → `{{slash:task-propose}} TNNNN`；还要改设计 → `{{slash:task-design}} TNNNN`。
