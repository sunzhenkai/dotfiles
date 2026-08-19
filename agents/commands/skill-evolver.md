---
id: skill-evolver
title: "Skill 进化"
description: 从多次真实执行中发现可复用改进，生成候选 Skill patch 并验证后再晋升；不要每次任务后自动改 Skill
category: Workflow
tags: [skill, evolve, workflow]
---

加载 skill `skill-evolver`，对已有 Skill 做一轮受控进化。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**输入**：可选目标 skill 名/路径，以及要纳入分析的经验（失败、纠正、重复路径）。未指定目标时先问，不猜。

## 门禁

1. 用户未点名进化 Skill 时，不要当本命令执行
2. 一次偶然失败不足以改 Skill
3. 未展示 Proposal 并获确认前，不写候选稿、不改生产 Skill

## 步骤

1. 收集 Experience（失败 / 成功 / 重复模式）
2. 判断是否值得进化；否则 `no-evolve` 并停止
3. 给出 Evolution Proposal，等待确认
4. 在 `evolutions/<date>-<slug>/` 写候选 patch，不直接改生产稿
5. Evaluate：回归成功路径 + 验证目标模式 + 跑已有测试（若有）
6. 用户确认后 Promote，或 Reject 并保留记录

详细约定见 skill `skill-evolver`。
