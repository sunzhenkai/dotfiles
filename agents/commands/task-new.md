---
id: task-new
title: "新建任务"
description: 按描述创建带编号的需求任务，并梳理涉及面（代码库等）
category: Workflow
tags: [task, workflow, openspec]
---

在 `tasks/YYYY-MM-DD/TNNNN-<slug>/` 创建需求任务，分配编号并更新 `tasks/INDEX.md`；仅对涉及面必须仓检出 `<prefix>-<slug>`，再写骨架（含工作上下文：是否 worktree、实际改动仓）。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-new` 职责）。机械步骤用 `taskctl`。开始时加载工作区 `.task-workflow.md`（`taskctl notes`）。

**输入**：同一条里 `{{slash:task-new}}` 后的正文就是需求；slug 可省略（自动推导）。本 command 的流程说明不是需求。能一句话概括要做什么就创建，不要要用户重述或确认 slug。只有完全没有主题（光秃命令、或整段都是套话）才问一句「要做什么」。

下一步：缺口偏方案 → `{{slash:task-explore}}`；范围已清 → `{{slash:task-propose}}`。
