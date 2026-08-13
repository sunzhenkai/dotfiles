---
id: task-explore
title: "探索方案"
description: 针对指定 task 探索方案，委托 openspec-explore
category: Workflow
tags: [task, workflow, openspec]
---

在已解析的 task 上下文中探索方案（不写业务代码）：resolve 后先 Checkout Gate，再委托 `openspec-explore`。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-explore` 职责）。机械步骤用 `taskctl`。

**输入**：任务编号（推荐 `T0001`）、slug 或路径；可省略（自动推断）；可选探索焦点。

下一步：继续探索 → `{{slash:task-explore}} TNNNN`；复杂/多方案 → `{{slash:task-design}} TNNNN`；范围已清 → `{{slash:task-propose}} TNNNN`。
