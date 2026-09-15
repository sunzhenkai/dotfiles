---
id: pwd-skill-manager
name: pwd-skill-manager
description: "本仓库套壳：只维护 agents/skills/ 下的公开共享 Skills。用户要求维护、修改、修复或重构本仓库共享 Skill 时使用；先做意图/冲突/公开性判断，再委托 skill-upgrader 的 patches 协议应用。不要用于安装外部 Skill、修改 agent 镜像目录或从真实经验自动进化 Skill。"
---

# PWD Skill Manager

面向用户的输出默认使用简体中文。命令、路径、代码和既成术语保持原文。

本 Skill 是当前工程的**项目级套壳**，位于 `.agents/skills/`。它维护公开共享 Skill 真相源 `agents/skills/<skill-name>/`，**不实现第二套 patch 语义**。

实现委托：完整读取仓库内 `agents/skills/skill-upgrader/SKILL.md` 及其 `references/patch-protocol.md`，按用户意图走 `update`（默认）或用户明确要求自进化结构时的 `self-upgrade`。下列增量约束与 `skill-upgrader` 冲突时，以本文件为准。

## 边界

- 目标必须是已有 `SKILL.md` 的 `agents/skills/<skill-name>/`。`<skill-dir>` 不得指向其它位置。
- 可修改该目录中的生产内容：`SKILL.md`、`references/`、`scripts/`、`assets/`、已有测试，以及 `self-upgrade` 所需的 `examples/` `evals/` `experience/`。
- 不修改 `.agents/skills/` 中除本 Skill 外的项目级 Skill，也不修改 `~/.agents/skills/`、用户主目录等同步生成或安装位置。本 Skill 自身的修改直接编辑 `.agents/skills/pwd-skill-manager/`，不走 `agents/skills/*/patches/`。
- 不负责搜索、安装或升级外部 Skill；此类请求交给相应的 Skill 商店流程。
- 不与 `skill-evolver` 混用。用户选择本 Skill 时走 `<skill-dir>/patches/`，不创建 `evolutions/`；用户明确选择 `skill-evolver` 或要求按执行经验进化时停止本流程。
- 从零创建公开 Skill 不属于“更新已有 Skill”；创建完成后的每轮修改必须遵守本协议。

## 强制前置判断

确定改动前，读取目标 `SKILL.md` 以及与请求直接相关的配套文件，并明确判断：

1. **意图**：模型要新增、删除或改变什么行为？触发场景和非目标是否明确？模式是 `update` 还是 `self-upgrade`？
2. **冲突**：是否与现有 frontmatter、门禁、流程、脚本、测试或其他 Skill 的职责冲突？
3. **合理性**：改动是否通用、可执行、可验证，是否值得写进公开共享 Skill？

任一项不明确或存在多种会显著改变结果的解释时，先向用户提出聚焦问题，不写 patch。发现请求不合理或冲突时，直接说明依据并给出最小替代方案；不得机械执行。

## 公开性约束

`agents/skills/` 面向公开复用：

- 不写入个人姓名、账号、主机名、绝对家目录、凭据、密钥、内部 URL、公司信息或私有仓库内容。
- 路径使用仓库相对路径或语义占位符，如 `<repo-root>`、`<skill-dir>`、`<skill-name>`。
- 示例使用虚构、通用数据，不复制当前会话中的隐私信息。
- 只加入跨项目或跨环境仍成立的规则；机器特例留在本地配置，不进入共享 Skill。
- 通用 Skill **不得**点名本 Skill，也不得点名仅存在于 `.agents/skills/` 的其它项目级工具，或写死本仓库布局（如 `dotf agents -c`、`scripts/agents/sync.sh`）。

## 委托流程

1. 确认仓库根。目标不存在、不在 `agents/skills/`、或名称不唯一时先询问。
2. 读取 `agents/skills/skill-upgrader/SKILL.md` 与 `references/patch-protocol.md`。
3. 完成本文件的前置判断与公开性检查。
4. 锁定唯一模式后，**按 skill-upgrader 该模式的工作流**写 `proposal.md`、`change.patch`、校验、门禁、应用、`result.md`。一次只处理一个目标 Skill、一种模式、一轮 patch。
5. `change.patch` 的 `a/` `b/` 路径必须是 `agents/skills/<skill-name>/...`；不得包含历史 `patches/`、agent 镜像或 `.agents/skills/`。
6. 风险表沿用 skill-upgrader。用户已明确批准具体改动内容可视为已通过对应门禁；笼统的「优化一下」不算批准中高风险 diff。
7. 不要自动执行 sync、commit 或 push。应用成功后可提醒 `dotf agents -c` 或 `scripts/agents/sync.sh`。

记录字段以 skill-upgrader 的 patch 协议为准；本仓额外要求见 [references/patch-protocol.md](references/patch-protocol.md)。

## 交付格式

沿用 skill-upgrader 交付块，并标明走的是本套壳：

```text
wrapper: pwd-skill-manager
skill: <skill-name>
path: agents/skills/<skill-name>
mode: update | self-upgrade
patch: <patch-id>
risk: low | medium | high
status: proposed | applied | failed | already-upgraded | aborted
change: <一句话>
validation: <通过项或失败原因>
next: <需要确认、sync 提醒、转 skill-evolver，或无>
```
