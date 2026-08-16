---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

在真实 delivery checkout 上持续实施 task 的 OpenSpec changes。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/apply.md` 及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；可附 change 范围和分支前缀。

只依据顶层 `result` 控制，逐条语义以 `references/apply.md` 的 outcome 表为准。跨阶段边界：`next` 时继续独立 candidate、已 defer 项并行挂起且禁止 testing/done；暂停类 outcome 停本轮调度并保持 `in_progress`，不宣称完成；只有 `done` 才允许对外完成并桥接 archive。用户决策或中断同样只停调度。
