---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

在真实 delivery checkout 上持续实施 task 的 OpenSpec changes。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/apply.md` 及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；可附 change 范围和分支前缀。

只要响应仍有 runnable `next` 就在同一轮继续；仅 done、deferred_only、全局阻塞、用户决策或用户中断时停止。
