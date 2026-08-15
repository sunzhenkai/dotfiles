---
id: task-archive
title: "归档任务"
description: 归档 task 关联的 OpenSpec changes，并移动 task 至 archive、更新索引
category: Workflow
tags: [task, workflow, openspec]
---

对已交付 task 执行 Initial preflight → External actions → Final preflight → finalize 的可恢复归档。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/archive.md` 及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；只可附 CLI 已以 code 2 精确请求且用户明确确认的 override。

输出 target 实际状态、external actions、delivery gate、Gate Overrides、非阻塞诊断和最终归档路径。
