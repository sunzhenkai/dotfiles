---
id: task-new
title: "新建任务"
description: 按描述创建带编号的需求任务，并梳理涉及面（代码库等）
category: Workflow
tags: [task, workflow, openspec]
---

在 `tasks/YYYY-MM-DD/TNNNN-<slug>/` 创建需求任务，分配编号并更新 `tasks/INDEX.md`；仅对涉及面必须仓检出 `<prefix>-<slug>`，再写骨架（含工作上下文：是否 worktree、实际改动仓）。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**第 0 步（第一条工具调用）**：把宿主渲染的**完整原文**写入临时文件（含标记后追加的正文与 `/task-new` 调用；禁止只重写 command 模板），执行

`python3 <task-workflow skill>/scripts/taskctl.py extract-new --message-file <该文件>`

- 退出码 0 / `empty=false` → 首条回复写 `需求：<requirement>`，立刻创建。禁止问「要做什么」，禁止要 slug。细节不足写入「现状缺口」。
- 退出码 2 / `empty=true` → 才问一句「要做什么」。

不要用「是否像流程说明 / 是否出现在本模板」自行判断；渲染后用户正文就在同一个 command block 里，减法规则会把需求抄成空。

然后读 skill `task-workflow` 的 `task-new` 节。机械步骤一律 `python3 <skill>/scripts/taskctl.py`（PATH 无 `taskctl`）。开始时 `notes`。

下一步：缺口偏方案 → `{{slash:task-explore}}`；范围已清 → `{{slash:task-propose}}`。

[TASK_NEW_INPUT_START]
