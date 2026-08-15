---
id: task-archive
title: "归档任务"
description: 归档 task 关联的 OpenSpec changes，并移动 task 至 archive、更新索引
category: Workflow
tags: [task, workflow, openspec]
---

按 `execution-context` 在真实 checkout 归档全部 OpenSpec change，把 `design/` 晋升到仓库正式位置（若有），再通过 Archive Completion Gate 原子移动 task 并更新索引。clean 只约束当前 task 的 delivery checkout；OpenSpec planning store 与保存 `tasks/` 的 task store 即使 dirty 也只作为非阻塞诊断，除非同一仓同时承担 delivery 角色。Prepare 产生的正式设计交付物若使 delivery dirty，先停下等待提交/合并，再 Finalize。仍有未完成 checkbox 时必须停下：逐条读原文，说明是「只差验证」还是「功能未完成」，交用户裁决；用户确认或明确「强行合并」后才用 `--force-merge`。任一 change 或 delta sync 失败必须停止。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**MUST 先读取并执行** skill `task-workflow`（`task-archive` 职责）。机械步骤用 `taskctl`（= `python3 <task-workflow skill>/scripts/taskctl.py`；PATH 无此命令，勿直接执行）。开始时加载工作区 `.task-workflow.md`（`taskctl notes` 或 `resolve` 的 `workflow_notes`）。

**输入**：任务编号（推荐 `T0001`）、slug 或路径；可省略（自动推断）。本条未写编号时，若本会话上文已有明确任务，MUST 当作已指定并显式传给 `resolve`，不要只把命令名放进 `--hint` 再让用户选。可选 PR/提交说明。
