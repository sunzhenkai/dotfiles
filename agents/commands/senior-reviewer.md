---
id: senior-reviewer
title: "Senior Reviewer"
description: 多视角高级审查：研发/产品/UI 设计/QA/运维等角色自动组合，审查系统或指定局部
category: Workflow
tags: [review, quality, workflow]
---

对 **整个系统** 或 **指定局部** 组织多视角高级审查，输出分级评审结论。

**Input**：可选目标（路径 / 模块 / diff 范围 / 方案文档）+ 可选指定视角。默认审查当前工作区变更，视角自动推断。

## 视角

预设：**研发、产品、UI 设计、QA、运维**。未指定时按目标内容自动推断（代码必有 研发+QA；涉 UI 加 UI 设计；新功能/方案加 产品；涉部署配置加 运维），推断结果在报告开头声明。

## 步骤

1. 界定审查范围（大目标先 `git diff --stat` / 文件清单摸规模，不全量通读）
2. 推断并声明启用视角
3. 分视角审查（支持时按视角并行派发 subagent），发现标注严重级别与 `path:line`
4. 跨视角去重汇总，按 Blocker / Major / Minor / Suggestion 分级输出报告
5. 只报告不改代码；不确定的发现标注置信度，不凑数

详细约定见 skill `senior-reviewer`。
