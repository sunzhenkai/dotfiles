---
id: role-based-reviewer
title: "角色化评审"
description: 可组合角色化只读评审。仅显式点名或指定岗位视角时使用，普通 review 不要自动触发
category: Workflow
tags: [review, quality, workflow]
---

按一个或多个岗位视角做只读问答或分级审查。**普通「帮我 review」不走本命令。**

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**输入**：可选 `roles=`、`mode=ask|review`、问题或变更范围。未指定角色时默认 engineer，不强行堆视角。`mode=review` 且未给范围时，默认审查当前工作区变更。

## 门禁

1. 未点名 / 未指定岗位 / 未要求跨角色时，不要当本命令执行
2. 推断将超过 2 个角色时先问用户
3. 默认只报 Blocker / Major，不主动报风格毛刺

## 角色

预设：`engineer`、`algo`、`data`、`sre`、`ops`、`biz`、`product`、`design`、`qa`。其它角色要有问题主体上的强信号才加。

## 步骤

1. 过门禁；界定范围（大目标先 `git diff --stat` / 文件清单摸规模，不全量通读）
2. 采用用户指定角色，或按强信号推断（默认 engineer）
3. 分角色审查或作答；review 默认只报 Blocker/Major 与 `path:line`
4. 跨角色去重汇总，保留主责归属
5. 只报告不改代码；不确定的发现标注置信度，不凑数

详细约定见 skill `role-based-reviewer`。
