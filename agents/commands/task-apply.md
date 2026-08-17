---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

在真实 delivery checkout 上持续实施 task 的 OpenSpec changes。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/apply.md` 及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；可附 change 范围和分支前缀。

只依据顶层 `result` 控制流程，逐条语义与汇报模板以 `references/apply.md` 为准；本轮禁止动作照 CLI 返回的 `next_action.forbidden` 执行。用户决策或中断同样只停本轮调度。
