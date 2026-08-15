---
id: task-propose
title: "提出提案"
description: 为指定 task 制定提案，委托 openspec-propose，保存一个或多个 changes
category: Workflow
tags: [task, workflow, openspec]
---

为已解析 task 生成并关联 apply-ready OpenSpec change。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/planning.md` 的 `task-propose` 小节及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；可附 change 拆分说明。

输出 changes、planning roots 和 apply 桥接。
