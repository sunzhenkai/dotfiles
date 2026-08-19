---
id: skill-upgrader
title: "Skill 升级"
description: 把已有 SKILL.md 升级为带 examples/evals/experience 的自进化 Skill；不根据一次失败改正文
category: Workflow
tags: [skill, upgrade, workflow]
---

加载 skill `skill-upgrader`，把一个已有 Skill 升级为具备经验积累、评估与持续进化能力的结构。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**输入**：目标 skill 名、id 或含 `SKILL.md` 的目录。未指定先问，不猜。

## 门禁

1. 用户未点名升级 Skill 为自进化时，不要当本命令执行
2. 没有现成 `SKILL.md` 就停止（本命令不从零创建）
3. 不要伪造 examples / experience
4. 不要根据经验改目标 Skill 的核心行为（那是 `skill-evolver`）

## 步骤

1. 完整读取现有 `SKILL.md`，保留原有目标、流程、约束
2. 幂等补齐 `examples/` `evals/` `experience/`（空目录不编历史）
3. 从原文抽取 Eval Cases，优先确定性判断
4. 在 `SKILL.md` 末尾追加自进化指令，不覆盖原文
5. 跑 Final Validation 清单后再交付

详细约定见 skill `skill-upgrader`。
