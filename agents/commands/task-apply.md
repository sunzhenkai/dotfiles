---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

在真实 delivery checkout 上持续实施 task 的 OpenSpec changes。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/apply.md` 及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；可附 change 范围和分支前缀。

只依据顶层 `result` 控制：`next` 时继续独立 candidate，已 defer 项并行挂起，禁止 testing/done；`blocked`、`deferred_only`、`validation_required` 时停本轮调度并汇报，保持 `in_progress`，不宣称完成；`validation_recorded` 只进入 done transition；只有 `done` 才允许对外完成并桥接 archive。用户决策或中断同样只停调度。仓级回归不是 final verification。
