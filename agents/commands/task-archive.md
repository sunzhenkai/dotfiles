---
id: task-archive
title: "归档任务"
description: 归档 task 关联的 OpenSpec changes，并移动 task 至 archive、更新索引
category: Workflow
tags: [task, workflow, openspec]
---

归档关联 OpenSpec change，把 `design/` 晋升到仓库正式位置（若有），再移动 task 目录并更新 `tasks/INDEX.md`。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-archive` 职责）。机械步骤用 `taskctl`。开始时加载工作区 `.task-workflow.md`（`taskctl notes` 或 `resolve` 的 `workflow_notes`）。

**输入**：任务编号（推荐 `T0001`）、slug 或路径；可省略（自动推断）。本条未写编号时，若本会话上文已有明确任务，MUST 当作已指定并显式传给 `resolve`，不要只把命令名放进 `--hint` 再让用户选。可选 PR/提交说明。
