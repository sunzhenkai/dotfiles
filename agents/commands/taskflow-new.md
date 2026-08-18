---
id: taskflow-new
title: "新建 taskflow 任务"
description: 按描述创建 driver change `{task}-driver`，写入涉及面与 driver 协议
category: Workflow
tags: [taskflow, workflow, openspec]
---

创建一个 taskflow driver change；只立身份与范围，不准备目标仓分支，不写 `tasks.md`。

**MUST** 读取 skill `taskflow`，然后只执行「脚手架」小节及其纪律条款。用户正文由 Agent 归纳为 kebab-case 的 `{task}`；不要调用脚本抽取需求，不要追问命名。正文确实为空时才问“要做什么？”。

输出 change name、`proposal.md` 路径、待确认的涉及面与验收标准空缺，以及 explore / propose 桥接（含 `openspec-propose` 应选“继续已有 change”的提示）。

[TASKFLOW_NEW_INPUT_START]
