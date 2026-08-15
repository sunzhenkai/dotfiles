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

**输入**：slug 可省略（自动推导）。命令系统会把用户在 `{{slash:task-new}}` 后输入的正文追加到本模板末尾；即使追加内容仍显示在同一个 command block 内，也属于本次需求，不能因为它位于 command block 内而当作流程说明丢弃。

执行前 MUST 先从追加内容或用户原始消息中写出一句「要做什么」的需求摘要。只要能写出摘要就立即创建，不要要求用户重述或确认 slug；细节不足写入「现状缺口」。只有追加内容为空，并且用户原始消息也完全没有改动主题时，才问一句「要做什么」。

下一步：缺口偏方案 → `{{slash:task-explore}}`；范围已清 → `{{slash:task-propose}}`。

`[TASK_NEW_INPUT_START]`——此标记是固定模板的结束边界；命令系统追加在其后的所有非空文本均为本次需求。
