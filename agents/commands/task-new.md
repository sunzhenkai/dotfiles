---
id: task-new
title: "新建任务"
description: 按描述创建带编号的需求任务，并梳理涉及面（代码库等）
category: Workflow
tags: [task, workflow, openspec]
---

创建一个编号 task；只记录计划范围，不准备目标仓分支。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/planning.md` 的 `task-new` 小节及其 safety 规则。用户正文由 Agent 归纳；不要调用脚本抽取需求，不要追问 slug。正文确实为空时才问“要做什么？”。

输出 ID、路径、现状缺口与 explore/propose 桥接。

[TASK_NEW_INPUT_START]
