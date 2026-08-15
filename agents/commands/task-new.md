---
id: task-new
title: "新建任务"
description: 按描述创建带编号的需求任务，并梳理涉及面（代码库等）
category: Workflow
tags: [task, workflow, openspec]
---

在 `tasks/YYYY-MM-DD/TNNNN-<slug>/` 创建需求任务，分配编号并更新 `tasks/INDEX.md`；仅对涉及面必须仓检出 `<prefix>-<slug>`，再写骨架（含工作上下文：是否 worktree、实际改动仓）。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**第 0 步：归纳需求（你自己做，不调工具）**

本条消息 = 固定模板 + 用户正文。用户正文通常追加在末尾（`[TASK_NEW_INPUT_START]` 之后）或跟在 `/task-new` 同一行。**归纳它，不要逐字比对模板做减法**：

1. 一句话概括本次需求 → 首条回复输出 `需求：<你的概括>`
2. 由概括得到 `--title`（简体中文可读标题）与 `--slug`（短英文 kebab-case，自行翻译，别音译整句）
3. 直接进入创建流程

只有整条消息除模板外**没有任何需求信息**（光秃 `/task-new`、只说「帮我建个任务」）才问一句「要做什么？」。信息不全（服务清单、目标文件、实现方式、验收细节缺失）**不是**追问理由——写进 README「现状缺口」。**禁止**追问 slug。

正例（MUST 直接创建）：`/task-new 给 docs/README 加一节本地安装说明` → `需求：给 docs/README 补本地安装说明` → `--title "补充 README 本地安装说明" --slug readme-local-install`。

**MUST 先读取并执行** skill `task-workflow`（`task-new` 职责节）。机械步骤一律 `python3 <task-workflow skill>/scripts/taskctl.py`（PATH 无 `taskctl`）。开始时 `notes`。

下一步：缺口偏方案 → `{{slash:task-explore}}`；范围已清 → `{{slash:task-propose}}`。

[TASK_NEW_INPUT_START]
