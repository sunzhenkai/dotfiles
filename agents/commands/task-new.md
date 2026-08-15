---
id: task-new
title: "新建任务"
description: 按描述创建带编号的需求任务，并梳理涉及面（代码库等）
category: Workflow
tags: [task, workflow, openspec]
---

在 `tasks/YYYY-MM-DD/TNNNN-<slug>/` 创建需求任务，分配编号并更新 `tasks/INDEX.md`；仅对涉及面必须仓检出 `<prefix>-<slug>`，再写骨架（含工作上下文：是否 worktree、实际改动仓）。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**第 0 步（先于读 skill、先于任何工具调用）**：本条消息里凡是**没有逐字出现在本模板**的自然语言，都是本次需求。把它原样抄出，并在首条回复输出一行 `需求：<原文>`。抄出非空 → 立刻进入创建流程；**禁止**追问「要做什么」、禁止要 slug、禁止给填写模板。服务清单、目标文件、实现方式、验收细节不全写入「现状缺口」，不是追问理由。

**MUST 先读取并执行** skill `task-workflow`（`task-new` 职责）。机械步骤用 `taskctl`（= `python3 <task-workflow skill>/scripts/taskctl.py`；PATH 无此命令，勿直接执行）。开始时加载工作区 `.task-workflow.md`（`taskctl notes`）。

**输入**：需求正文——命令系统把它追加到本模板末尾，仍显示在同一个 command block 内，不能因此当作流程说明丢弃；slug 可省略，自行推导。只有抄出为空（本条逐字等于本模板全文）才问一句「要做什么」。

下一步：缺口偏方案 → `{{slash:task-explore}}`；范围已清 → `{{slash:task-propose}}`。

`[TASK_NEW_INPUT_START]` 是固定模板的结束边界；其后所有非空文本均为本次需求。
