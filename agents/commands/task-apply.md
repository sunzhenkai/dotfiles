---
id: task-apply
title: "实施任务"
description: 执行 task 关联的 OpenSpec changes（含目标仓分支准备）
category: Workflow
tags: [task, workflow, openspec]
---

在准备好的交付分支上持续实施 task 的 OpenSpec changes。

**MUST** 读取 skill `task-workflow`，然后只执行 `references/apply.md` 及其 safety 规则。输入可为 TNNNN、slug、路径或会话中已明确的唯一 task；可附 change 范围和分支前缀。

进度只认 OpenSpec `tasks.md` 的 checkbox：`taskctl status` 给出的 remaining 就是待做项，勾选即记账。持续推进到 `references/apply.md` 允许的结束条件为止——单项暂缓和汇报点都不结束本轮。只有 checkbox 全勾且验证已写入才允许宣称完成，其余情况 task 保持 `in_progress`。
